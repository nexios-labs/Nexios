from __future__ import annotations

import inspect
import typing

from typing_extensions import Annotated, Doc

from nexios import logging
from nexios.http import Request, Response
from nexios.middleware.base import BaseMiddleware

from .base import AuthenticationBackend, UnauthenticatedUser

logger = logging.create_logger(__name__)


class AuthenticationMiddleware(BaseMiddleware):
    """
    Middleware responsible for handling user authentication.

    This middleware intercepts incoming HTTP requests, processes them through one or more
    authentication backends, and attaches the authenticated user to the request scope.
    Processing stops at the first backend that successfully authenticates the user.

    Attributes:
        backends (list[AuthenticationBackend]): List of authentication backends to try.
    """

    def __init__(
        self,
        backend: Annotated[
            typing.Union[AuthenticationBackend, typing.List[AuthenticationBackend]],
            Doc("Single backend or list of backends to use for authentication."),
        ],
    ) -> None:
        """
        Initialize the authentication middleware with one or more backends.

        Args:
            backends: Single backend or list of backends to use for authentication.
                     Each backend will be tried in order until one successfully
                     authenticates the user or all backends are exhausted.
        """
        if isinstance(backend, AuthenticationBackend):
            self.backends = [backend]
        else:
            self.backends = backend

    async def process_request(
        self,
        request: Annotated[
            Request,
            Doc("The HTTP request object, containing authentication credentials."),
        ],
        response: Annotated[
            Response,
            Doc(
                "The HTTP response object, which may be modified during authentication."
            ),
        ],
        call_next: typing.Callable[..., typing.Awaitable[typing.Any]],
    ) -> None:
        """
        Process an incoming request through all authentication backends until one succeeds.

        This method iterates through each backend in order, attempting to authenticate
        the request. If a backend successfully authenticates the user, the user and
        authentication method are stored in the request scope and processing stops.
        If no backend authenticates the user, an unauthenticated user is set.

        Args:
            request: The incoming HTTP request.
            response: The HTTP response that will be sent.
            call_next: The next middleware or route handler in the chain.
        """
        # Try each backend until one successfully authenticates the user
        for backend in self.backends:
            try:
                if inspect.iscoroutinefunction(backend.authenticate):
                    user = await backend.authenticate(request, response)
                else:
                    user = backend.authenticate(request, response)  # type: ignore

                if user is not None:
                    # Authentication successful, store user and auth type
                    request.scope["user"] = user[0]
                    request.scope["auth"] = user[-1]
                    break

            except Exception as e:
                # Log the error but continue to the next backend
                logger.error(
                    f"Error in {backend.__class__.__name__} authentication: {str(e)}"
                )
                continue
        else:
            # No backend authenticated the user
            request.scope["user"] = UnauthenticatedUser()
            request.scope["auth"] = "no-auth"

        await call_next()
