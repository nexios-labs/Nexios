from __future__ import annotations
from enum import Enum
from typing import Callable, Type, Awaitable, Any
import typing
from .http.request import Request
from .http.response import NexiosResponse as Response
from .websockets import WebSocket


AppType = typing.TypeVar("AppType")

Scope = typing.MutableMapping[str, typing.Any]
Message = typing.MutableMapping[str, typing.Any]

Receive = typing.Callable[[], typing.Awaitable[Message]]
Send = typing.Callable[[Message], typing.Awaitable[None]]
RequestResponseEndpoint = typing.Callable[[Request], typing.Awaitable[Response]]

MiddlewareType = typing.Callable[
    [Request, Response, RequestResponseEndpoint], typing.Awaitable[Response]
]
WsMiddlewareType = Callable[
    [Type[WebSocket], Type[Callable[..., Awaitable[Message]]]], Type[Send]
]

WsHandlerType = typing.Callable[[WebSocket], typing.Awaitable[None]]
HandlerType = Callable[[Request, Response], Awaitable[Any]]
ExceptionHandlerType = Callable[
    [Request, Response, Exception], typing.Coroutine[Any, Any, Any]
]

ASGIApp = typing.Callable[[Scope, Receive, Send], typing.Awaitable[None]]
