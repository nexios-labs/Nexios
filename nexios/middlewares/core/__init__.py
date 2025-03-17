from __future__ import annotations

import typing

import anyio

from contextlib import contextmanager
from nexios.http.request import ClientDisconnect, Request
from nexios.http.response import  NexiosResponse as Response
from nexios.types import ASGIApp, Message, Receive, Scope, Send
from nexios.websockets import WebSocket
RequestResponseEndpoint = typing.Callable[[Request], typing.Awaitable[Response]]
DispatchFunction = typing.Callable[[Request, Response,typing.Coroutine[None,None,typing.Any]], typing.Awaitable[Response]]
T = typing.TypeVar("T")

import sys
from collections.abc import Iterator
from typing import Any, Protocol

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import ParamSpec
else:  # pragma: no cover
    from typing_extensions import ParamSpec

from nexios.types import ASGIApp

P = ParamSpec("P")
has_exceptiongroups = True
if sys.version_info < (3, 11):  # pragma: no cover
    try:
        from exceptiongroup import BaseExceptionGroup  # type: ignore[unused-ignore,import-not-found]
    except ImportError:
        has_exceptiongroups = False

@contextmanager
def collapse_excgroups() -> typing.Generator[None, None, None]:
    try:
        yield
    except BaseException as exc:
        if has_exceptiongroups:  # pragma: no cover
            while isinstance(exc, BaseExceptionGroup) and len(exc.exceptions) == 1: #type:ignore
                exc = exc.exceptions[0]  #type:ignore

        raise exc

class _MiddlewareFactory(Protocol[P]):
    def __call__(self, app: ASGIApp, /, *args: P.args, **kwargs: P.kwargs) -> ASGIApp: ...  # pragma: no cover


class Middleware:
    def __init__(
        self,
        cls: _MiddlewareFactory[P],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        self.cls = cls
        self.args = args
        self.kwargs = kwargs

    def __iter__(self) -> Iterator[Any]:
        as_tuple = (self.cls, self.args, self.kwargs)
        return iter(as_tuple)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        args_strings = [f"{value!r}" for value in self.args]
        option_strings = [f"{key}={value!r}" for key, value in self.kwargs.items()]
        name = getattr(self.cls, "__name__", "")
        args_repr = ", ".join([name] + args_strings + option_strings)
        return f"{class_name}({args_repr})"


class _CachedRequest(Request):
    """
    If the user calls Request.body() from their dispatch function
    we cache the entire request body in memory and pass that to downstream middlewares,
    but if they call Request.stream() then all we do is send an
    empty body so that downstream things don't hang forever.
    """

    def __init__(self, scope: Scope, receive: Receive):
        super().__init__(scope, receive)
        self._wrapped_rcv_disconnected = False
        self._wrapped_rcv_consumed = False
        self._wrapped_rc_stream = self.stream()

    async def wrapped_receive(self) -> Message:
        # wrapped_rcv state 1: disconnected
        if self._wrapped_rcv_disconnected:
            # we've already sent a disconnect to the downstream app
            # we don't need to wait to get another one
            # (although most ASGI servers will just keep sending it)
            return {"type": "http.disconnect"}
        # wrapped_rcv state 1: consumed but not yet disconnected
        if self._wrapped_rcv_consumed:
            # since the downstream app has consumed us all that is left
            # is to send it a disconnect
            if self._is_disconnected:
                # the middleware has already seen the disconnect
                # since we know the client is disconnected no need to wait
                # for the message
                self._wrapped_rcv_disconnected = True
                return {"type": "http.disconnect"}
            # we don't know yet if the client is disconnected or not
            # so we'll wait until we get that message
            msg = await self.receive()
            if msg["type"] != "http.disconnect":  # pragma: no cover
                # at this point a disconnect is all that we should be receiving
                # if we get something else, things went wrong somewhere
                raise RuntimeError(f"Unexpected message received: {msg['type']}")
            self._wrapped_rcv_disconnected = True
            return msg

        # wrapped_rcv state 3: not yet consumed
        if getattr(self, "_body", None) is not None:
            # body() was called, we return it even if the client disconnected
            self._wrapped_rcv_consumed = True
            return {
                "type": "http.request",
                "body": self._body,
                "more_body": False,
            }
        elif self._stream_consumed:
            # stream() was called to completion
            # return an empty body so that downstream apps don't hang
            # waiting for a disconnect
            self._wrapped_rcv_consumed = True
            return {
                "type": "http.request",
                "body": b"",
                "more_body": False,
            }
        else:
            # body() was never called and stream() wasn't consumed
            try:
                stream = self.stream()
                chunk = await stream.__anext__()
                self._wrapped_rcv_consumed = self._stream_consumed
                return {
                    "type": "http.request",
                    "body": chunk,
                    "more_body": not self._stream_consumed,
                }
            except ClientDisconnect:
                self._wrapped_rcv_disconnected = True
                return {"type": "http.disconnect"}


class BaseMiddleware:
    def __init__(self, app: ASGIApp, dispatch: DispatchFunction) -> None:
        self.app = app
        self.dispatch_func = dispatch

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = _CachedRequest(scope, receive)
        response = Response()
        
        wrapped_receive = request.wrapped_receive
        response_sent = anyio.Event()

        async def call_next() -> Response:
            app_exc: Exception | None = None

            async def receive_or_disconnect() -> Message:
                if response_sent.is_set():
                    return {"type": "http.disconnect"}

                async with anyio.create_task_group() as task_group:

                    async def wrap(func: typing.Callable[[], typing.Awaitable[T]]) -> T:
                        result = await func()
                        task_group.cancel_scope.cancel()
                        return result

                    task_group.start_soon(wrap, response_sent.wait)
                    message = await wrap(wrapped_receive)

                if response_sent.is_set():
                    return {"type": "http.disconnect"}

                return message

            async def send_no_error(message: Message) -> None:
                try:
                    await send_stream.send(message)
                except anyio.BrokenResourceError:
                    # recv_stream has been closed, i.e. response_sent has been set.
                    return

            async def coro() -> None:
                nonlocal app_exc

                with send_stream:
                    try:
                        await self.app(scope, receive_or_disconnect, send_no_error)
                    except Exception as exc:
                        app_exc = exc

            task_group.start_soon(coro)

            try:
                message = await recv_stream.receive()
                info = message.get("info", None)
                if message["type"] == "http.response.debug" and info is not None:
                    message = await recv_stream.receive()
            except anyio.EndOfStream:
                if app_exc is not None:
                    raise app_exc
                raise RuntimeError("No response returned.")

            assert message["type"] == "http.response.start"

            async def body_stream() -> typing.AsyncGenerator[bytes, None]:
                async for message in recv_stream:
                    assert message["type"] == "http.response.body"
                    body = message.get("body", b"")
                    if body:
                        yield body
                    if not message.get("more_body", False):
                        break

                if app_exc is not None:
                    raise app_exc

            response_ = response.stream(iterator=body_stream(),status_code=message["status"]) #type: ignore
            response_._response._headers = message["headers"] #type: ignore
            return response
            

        streams: anyio.create_memory_object_stream[Message] = anyio.create_memory_object_stream() #type: ignore
        send_stream, recv_stream = streams
        with recv_stream, send_stream, collapse_excgroups():
            async with anyio.create_task_group() as task_group:
                await self.dispatch_func(request, response, call_next) #type: ignore
                await response.get_response()(scope, wrapped_receive, send)
                response_sent.set()
                recv_stream.close()
                

WebSocketDispatchFunction = typing.Callable[
    ['WebSocket', typing.Coroutine[None, None, typing.Any]],
    typing.Awaitable[None]
]


MiddlewareType = typing.Callable[[Request,Response,typing.Coroutine[None,None,Any]], typing.Awaitable[typing.Any]]
def wrap_middleware(middleware_function :MiddlewareType) -> Middleware:
    return Middleware(BaseMiddleware, dispatch = middleware_function)
__all__ = [
    "BaseMiddleware"
]


