from typing import Any, Callable, List, Union
from .routing import Router, WSRouter, WebsocketRoutes,Routes
import  typing
from .exception_handler import ExceptionMiddleware
from typing_extensions import Doc, Annotated  # type:ignore
from nexios.config import MakeConfig
from typing import Awaitable, Optional, AsyncIterator
from nexios.logging import getLogger
from nexios.middlewares.core import BaseMiddleware
from nexios.middlewares.core import Middleware
from nexios.middlewares.errors.server_error_handler import ServerErrorMiddleware,ServerErrHandlerType
from nexios.structs import URLPath

from .types import (
    MiddlewareType,
    Scope,
    Send,
    Receive,
    Message,
    HandlerType,
    ASGIApp
)

allowed_methods_default = ["get", "post", "delete", "put", "patch", "options"]

from typing import Dict, Any

AppType = typing.TypeVar("AppType", bound="NexiosApp")


logger = getLogger("nexios")



class NexiosApp(object):
    def __init__(
        self,
        config: Annotated[
            Optional[MakeConfig],
            Doc(
                """
                    This subclass is derived from the MakeConfig class and is responsible for managing configurations within the Nexios framework. It takes arguments in the form of dictionaries, allowing for structured and flexible configuration handling. By using dictionaries, this subclass makes it easy to pass multiple configuration values at once, reducing complexity and improving maintainability.

                    One of the key advantages of this approach is its ability to dynamically update and modify settings without requiring changes to the core codebase. This is particularly useful in environments where configurations need to be frequently adjusted, such as database settings, API credentials, or feature flags. The subclass can also validate the provided configuration data, ensuring that incorrect or missing values are handled properly.

                    Additionally, this design allows for merging and overriding configurations, making it adaptable for various use cases. Whether used for small projects or large-scale applications, this subclass ensures that configuration management remains efficient and scalable. By extending MakeConfig, it leverages existing functionality while adding new capabilities tailored to Nexios. This makes it an essential component for maintaining structured and well-organized application settings.
                    """
            ),
        ] = None,
        middlewares: Annotated[
            List[Middleware],
            Doc(
                "A list of middlewares, where each middleware is either a class inherited from BaseMiddleware or an asynchronous callable function that accepts request, response, and callnext"
            ),
        ] = [],
        server_error_handler: Annotated[
            Optional[ServerErrHandlerType],
            Doc(
                """
                        A function in Nexios responsible for handling server-side exceptions by logging errors, reporting issues, or initiating recovery mechanisms. It prevents crashes by intercepting unexpected failures, ensuring the application remains stable and operational. This function provides a structured approach to error management, allowing developers to define custom handling strategies such as retrying failed requests, sending alerts, or gracefully degrading functionality. By centralizing error processing, it improves maintainability and observability, making debugging and monitoring more efficient. Additionally, it ensures that critical failures do not disrupt the entire system, allowing services to continue running while appropriately managing faults and failures."""
            ),
        ] = None,
        lifespan: Optional[Callable[["NexiosApp"], AsyncIterator[None]]] = None,
    ):
        self.config = config
        self.server_error_handler = None
        super().__init__()
        self.ws_router = WSRouter()
        self.ws_routes: List[WebsocketRoutes] = []
        self.http_middlewares: List[Middleware] =  middlewares or []
        self.ws_middlewares: List[ASGIApp] = []
        self.startup_handlers: List[Callable[[], Awaitable[None]]] = []
        self.shutdown_handlers: List[Callable[[], Awaitable[None]]] = []
        self.exceptions_handler: Any[ExceptionMiddleware, None] = (
            server_error_handler or ExceptionMiddleware()
        )
        
        self.app = Router()
        self.router = self.app
        self.route = self.router.route
        self.lifespan_context :Optional[Callable[["NexiosApp"], AsyncIterator[None]]] = lifespan
       

    def on_startup(self, handler: Callable[[], Awaitable[None]]) -> None:
        """
        Registers a startup handler that executes when the application starts.

        This method allows you to define functions that will be executed before
        the application begins handling requests. It is useful for initializing
        resources such as database connections, loading configuration settings,
        or preparing caches.

        The provided function must be asynchronous (`async def`) since it
        will be awaited during the startup phase.

        Args:
            handler (Callable): An asynchronous function to be executed at startup.

        Returns:
            Callable: The same handler function, allowing it to be used as a decorator.

        Example:
            ```python

            @app.on_startup
            async def connect_to_db():
                global db
                db = await Database.connect("postgres://user:password@localhost:5432/mydb")
                print("Database connection established.")

            @app.on_startup
            async def cache_warmup():
                global cache
                cache = await load_initial_cache()
                print("Cache warmed up and ready.")
            ```

        In this example:
        - `connect_to_db` establishes a database connection before the app starts.
        - `cache_warmup` preloads data into a cache for faster access.

        These functions will be executed in the order they are registered when the
        application starts.
        """
        self.startup_handlers.append(handler)

    def on_shutdown(self, handler: Callable[[], Awaitable[None]]) -> None:
        """
        Registers a shutdown handler that executes when the application is shutting down.

        This method allows you to define functions that will be executed when the
        application is stopping. It is useful for cleaning up resources such as
        closing database connections, saving application state, or gracefully
        terminating background tasks.

        The provided function must be asynchronous (`async def`) since it will be
        awaited during the shutdown phase.

        Args:
            handler (Callable): An asynchronous function to be executed during shutdown.

        Returns:
            Callable: The same handler function, allowing it to be used as a decorator.

        Example:
            ```python
            app = NexioApp()

            @app.on_shutdown
            async def disconnect_db():
                global db
                await db.disconnect()
                print("Database connection closed.")

            @app.on_shutdown
            async def clear_cache():
                global cache
                await cache.clear()
                print("Cache cleared before shutdown.")
            ```

        In this example:
        - `disconnect_db` ensures that the database connection is properly closed.
        - `clear_cache` removes cached data to free up memory before the app stops.

        These functions will be executed in the order they are registered when the
        application is shutting down.
        """
        self.shutdown_handlers.append(handler)

    async def _startup(self) -> None:
        """Execute all startup handlers sequentially"""
        for handler in self.startup_handlers:
            try:
                await handler()
            except Exception as e:
                raise e

    async def _shutdown(self) -> None:
        """Execute all shutdown handlers sequentially with error handling"""
        for handler in self.shutdown_handlers:
            try:
                await handler()
            except Exception as e:
                raise e

    async def handle_lifespan(self, receive: Receive, send: Send) -> None:
        """Handle ASGI lifespan protocol events."""
        try:
            while True:
                message: Message = await receive()
                if message["type"] == "lifespan.startup":
                    try:
                        if self.lifespan_context:
                            # If a lifespan context manager is provided, use it
                            self.lifespan_manager :Any  = self.lifespan_context(self)
                            await self.lifespan_manager.__aenter__()
                        else:
                            # Otherwise, fall back to the default startup handlers
                            await self._startup()
                        await send({"type": "lifespan.startup.complete"})
                    except Exception as e:
                        await send({"type": "lifespan.startup.failed", "message": str(e)})
                        return

                elif message["type"] == "lifespan.shutdown":
                    try:
                        if self.lifespan_context:
                            # If a lifespan context manager is provided, use it
                            await self.lifespan_manager.__aexit__(None, None, None)
                        else:
                            # Otherwise, fall back to the default shutdown handlers
                            await self._shutdown()
                        await send({"type": "lifespan.shutdown.complete"})
                        return
                    except Exception as e:
                        await send({"type": "lifespan.shutdown.failed", "message": str(e)})
                        return

        except Exception as e:
            if message["type"].startswith("lifespan.startup"):  # type: ignore
                await send({"type": "lifespan.startup.failed", "message": str(e)})
            else:
                await send({"type": "lifespan.shutdown.failed", "message": str(e)})

        except Exception as e: #type:ignore
            if message["type"].startswith("lifespan.startup"):  # type: ignore
                await send({"type": "lifespan.startup.failed", "message": str(e)})
            else:
                await send({"type": "lifespan.shutdown.failed", "message": str(e)})

   

    
    
    def add_middleware(
        self,
        middleware: Annotated[
            MiddlewareType,
            Doc(
                "A callable middleware function that processes requests and responses."
            ),
        ],
    ) -> None:
        """
        Adds middleware to the application.

        Middleware functions are executed in the request-response lifecycle, allowing
        modifications to requests before they reach the route handler and responses
        before they are sent back to the client.

        Args:
            middleware (MiddlewareType): A callable that takes a `Request`, `Response`,
            and a `Callable` (next middleware or handler) and returns a `Response`.

        Returns:
            None

        Example:
            ```python
            def logging_middleware(request: Request, response: Response, next_call: Callable) -> Response:
                print(f"Request received: {request.method} {request.url}")
                return next_call(request, response)

            app.add_middleware(logging_middleware)
            ```
        """
        
        self.http_middlewares.insert(0,Middleware(BaseMiddleware, dispatch = middleware)) #type:ignore
    
    def add_ws_route(
        self, 
        route: Annotated[WebsocketRoutes, Doc("An instance of the Routes class representing a WebSocket route.")]
    ) -> None:
        """
        Adds a WebSocket route to the application.

        This method registers a WebSocket route, allowing the application to handle WebSocket connections.

        Args:
            route (Routes): The WebSocket route configuration.

        Returns:
            None

        Example:
            ```python
            route = Routes("/ws/chat", chat_handler)
            app.add_ws_route(route)
            ```
        """
        self.ws_router.add_ws_route(route)
        
    def ws_route(self, route :str):
        
        return self.ws_router.ws_route(route)
    def mount_router(self,router :Router, path :typing.Optional[str] = None):
        """
        Mounts a router and all its routes to the application.

        This method allows integrating another `Router` instance, registering all its
        defined routes into the current application. It is useful for modularizing routes
        and organizing large applications.

        Args:
            router (Router): The `Router` instance whose routes will be added.

        Returns:
            None

        Example:
            ```python
            user_router = Router()

            @user_router.route("/users", methods=["GET"])
            def get_users(request, response):
                 response.json({"users": ["Alice", "Bob"]})

            app.mount_router(user_router)  # Mounts the user routes into the main app
            ```
        """
        self.router.mount_router(router, path=path)
        
    def mount_ws_router(
        self,
        router: Annotated[
            "WSRouter",
            Doc("An instance of Router containing multiple routes to be mounted."),
        ],
    ) -> None:
        """
        Mounts a router and all its routes to the application.

        This method allows integrating another `Router` instance, registering all its
        defined routes into the current application. It is useful for modularizing routes
        and organizing large applications.

        Args:
            router (Router): The `Router` instance whose routes will be added.

        Returns:
            None

        Example:
            ```python
            chat_router = WSRouter()

            @chat_router.ws("/users")
            def get_users(ws):
                ...

            app.mount_ws_router(chat_router)  # Mounts the user routes into the main app
            ```
        """
        self.ws_router.mount_router(router)

    
            

    async def handle_websocket(self, scope: Scope, receive: Receive, send: Send) -> None:
        app = self.ws_router
        for mdw in reversed(self.ws_middlewares):
            app =   mdw(app) #type:ignore
        await app(scope, receive, send)
            

    def add_ws_middleware(
        self,
        middleware: Annotated[
            ASGIApp,
            Doc(
                "A callable function that intercepts and processes WebSocket connections."
            ),
        ],
    ) -> None:
        """
        Adds a WebSocket middleware to the application.

        WebSocket middleware functions allow pre-processing of WebSocket requests before they
        reach their final handler. Middleware can be used for authentication, logging, or
        modifying the WebSocket request/response.

        Args:
            middleware (Callable): A callable function that handles WebSocket connections.

        Returns:
            None

        Example:
            ```python
            def ws_auth_middleware(ws, next_handler):
                if not ws.headers.get("Authorization"):
                    ...
                return next_handler(ws)

            app.add_ws_middleware(ws_auth_middleware)
            ```
        """
        self.ws_middlewares.append(middleware)
    
    def handle_http_request(self) -> Router:
        app = self.router
        middleware = (
            [Middleware(BaseMiddleware, dispatch = ServerErrorMiddleware(handler=self.server_error_handler))] +
            self.http_middlewares +
            [Middleware(BaseMiddleware, dispatch =self.exceptions_handler)]
            
        )
        for cls, args, kwargs in reversed(middleware):
            app = cls(app,*args,**kwargs)
        return app
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI application callable"""
        scope['app'] = self
        if scope["type"] == "lifespan":
            await self.handle_lifespan(receive, send)
        elif scope["type"] == "http":
            await self.handle_http_request()(scope, receive, send)

        else:
            
            await self.handle_websocket(scope, receive, send)

   
   
   
    def get(
        self,
        path: Annotated[
            str,
            Doc("The URL path pattern for the endpoint. Supports dynamic parameters using curly brace syntax.")
        ],
        name: Annotated[
            Optional[str],
            Doc("A unique name for the route.")
        ] = None,
        middlewares : Annotated[
            List[Any],
            Doc("Optional Middleware that should be executed before the route handler")
         ] = [],
        **kwargs: Annotated[
            Dict[str, Any],
            Doc("Additional arguments to pass to the Routes class.")
        ]
    ) -> Callable[..., Any]:
        """
        Registers a GET route.

        This decorator allows you to define an endpoint that handles HTTP GET requests. 
        GET requests are typically used for retrieving resources.

        Args:
            route (Routes): The route definition, including path and handler function.
            validator (Callable, optional): A function to validate the request data before passing it to the handler.

        Returns:
            Callable: The decorated handler function.

        Example:
            ```python
            @app.get("/users")
            async def get_users(request,response):
                return response.json({"users": ["Alice", "Bob"]})
            ```
        """
        return self.route(path=f"{path}", 
                           methods=["GET"], 
                           name=name,
                           middlewares = middlewares,
                            **kwargs)


    def post(
        self,
        path: Annotated[
            str,
            Doc("The URL path pattern for the endpoint. Supports dynamic parameters using curly brace syntax.")
        ],
        name: Annotated[
            Optional[str],
            Doc("A unique name for the route.")
        ] = None,
        middlewares : Annotated[
            List[Any],
            Doc("Optional Middleware that should be executed before the route handler")
        ] = [],
       
        **kwargs: Annotated[
            Dict[str, Any],
            Doc("Additional arguments to pass to the Routes class.")
        ]
    ) -> Callable[..., Any]:
        """
        Registers a POST route.

        This decorator is used to define an endpoint that handles HTTP POST requests, 
        typically for creating resources.

        Args:
            route (Routes): The route definition, including path and handler function.
            validator (Callable, optional): A function to validate the request data before passing it to the handler.

        Returns:
            Callable: The decorated handler function.

        Example:
            ```python
            @app.post("/users")
            async def create_user(request,response):
                return response.json({"message": "User created"})
            ```
        """
        return self.route(path=f"{path}", 
                           methods=["POST"], 
                           name=name,
                           middlewares = middlewares,
                            **kwargs)


    def delete(
        self,
        path: Annotated[
            str,
            Doc("The URL path pattern for the endpoint. Supports dynamic parameters using curly brace syntax.")
        ],
        name: Annotated[
            Optional[str],
            Doc("A unique name for the route.")
        ] = None,
        middlewares : Annotated[
            List[Any],
            Doc("Optional Middleware that should be executed before the route handler")
        ] = [],
       
        **kwargs: Annotated[
            Dict[str, Any],
            Doc("Additional arguments to pass to the Routes class.")
        ]
    ) -> Callable[..., Any]:
        """
        Registers a DELETE route.

        This decorator allows defining an endpoint that handles HTTP DELETE requests, 
        typically for deleting resources.

        Args:
            route (Routes): The route definition, including path and handler function.
            validator (Callable, optional): A function to validate the request data before passing it to the handler.

        Returns:
            Callable: The decorated handler function.

        Example:
            ```python
            @app.delete("/users/{user_id}")
            def delete_user(request, response):
                user_id = request.path_params.user_id
                return responsejson({"message": f"User {user_id} deleted"})
            ```
        """
        return self.route(path=f"{path}", 
                           methods=["DELETE"],                      
                           name=name,
                           middlewares = middlewares,
                            **kwargs)


    def put(
        self,
        path: Annotated[
            str,
            Doc("The URL path pattern for the endpoint. Supports dynamic parameters using curly brace syntax.")
        ],
        name: Annotated[
            Optional[str],
            Doc("A unique name for the route.")
        ] = None,
        middlewares : Annotated[
            List[Any],
            Doc("Optional Middleware that should be executed before the route handler")
        ] = [],
        **kwargs: Annotated[
            Dict[str, Any],
            Doc("Additional arguments to pass to the Routes class.")
        ]
    ) -> Callable[..., Any]:
        """
        Registers a PUT route.

        This decorator defines an endpoint that handles HTTP PUT requests, 
        typically for updating or replacing a resource.

        Args:
            route (Routes): The route definition, including path and handler function.
            validator (Callable, optional): A function to validate the request data before passing it to the handler.

        Returns:
            Callable: The decorated handler function.

        Example:
            ```python
            @app.delete("/users/{user_id}")
            def delete_user(request, response):
                user_id = request.path_params.user_id
                return responsejson({"message": f"User {user_id} updated"})
        """
        return self.route(path=f"{path}", 
                           methods=["PUT"], 
                           name=name,
                           middlewares = middlewares,
                            **kwargs)

    def patch(
        self,
        path: Annotated[
            str,
            Doc("The URL path pattern for the endpoint. Supports dynamic parameters using curly brace syntax.")
        ],
        name: Annotated[
            Optional[str],
            Doc("A unique name for the route.")
        ] = None,
        middlewares : Annotated[
            List[Any],
            Doc("Optional Middleware that should be executed before the route handler")
        ] = [],
       
        **kwargs: Annotated[
            Dict[str, Any],
            Doc("Additional arguments to pass to the Routes class.")
        ]
    ) -> Callable[..., Any]:
        """
        Registers a PATCH route.

        This decorator defines an endpoint that handles HTTP PATCH requests, 
        which are used to apply partial modifications to a resource.

        Args:
            route (Routes): The route definition, including path and handler function.
            validator (Callable, optional): A function to validate the request data before passing it to the handler.

        Returns:
            Callable: The decorated handler function.

        Example:
            ```python
            @app.patch("/users/{user_id}")
            def partial_update_user(request, response):
                user_id = request.path_params.user_id
            
                return respoonse.json({"message": f"User {user_id} partially updated"})
            ```
        """
        return self.route(path=f"{path}", 
                           methods=["PATCH"], 
                           name=name,
                           middlewares = middlewares,
                            **kwargs)


    def options(
        self,
        path: Annotated[
            str,
            Doc("The URL path pattern for the endpoint. Supports dynamic parameters using curly brace syntax.")
        ],
        name: Annotated[
            Optional[str],
            Doc("A unique name for the route.")
        ] = None,
        middlewares : Annotated[
            List[Any],
            Doc("Optional Middleware that should be executed before the route handler")
        ] = []
    ) -> Callable[..., Any]:
        """
        Registers an OPTIONS route.

        This decorator defines an endpoint that handles HTTP OPTIONS requests, 
        which are used to describe the communication options for the target resource. 
        OPTIONS requests are commonly used in CORS (Cross-Origin Resource Sharing) 
        to check allowed methods, headers, and authentication rules.

        Args:
            route (Routes): The route definition, including path and handler function.
            validator (Callable, optional): A function to validate the request data before passing it to the handler.

        Returns:
            Callable: The decorated handler function.

        Example:
            ```python
            @app.options("/users")
            def options_users(request):
                return response.json({
                    "Allow": "GET, POST, DELETE, OPTIONS"
                })
            ```
        """
        return self.route(path=f"{path}", 
                           methods=["OPTIONS"], 
                           name=name,
                           middlewares=middlewares
                            )



    def head(
        self,
        path: Annotated[
            str,
            Doc("The URL path pattern for the endpoint. Supports dynamic parameters using curly brace syntax.")
        ],

        name: Annotated[
            Optional[str],
            Doc("A unique name for the route.")
        ] = None,
        middlewares : Annotated[
            List[Any],
            Doc("Optional Middleware that should be executed before the route handler")
        ] = [],
        **kwargs: Annotated[
            Dict[str, Any],
            Doc("Additional arguments to pass to the Routes class.")
        ]
    ) -> Callable[..., Any]:
        
         return self.route(path=f"{path}", 
                           methods=["HEAD"], 
                           name=name,
                           middlewares = [],
                            **kwargs)

    
    def add_route(
        self, 
        route: Annotated[Routes, 
                         Doc("An instance of the Routes class representing an HTTP route.")]
    ) -> None:
        """
        Adds an HTTP route to the application.

        This method registers an HTTP route, allowing the application to handle requests for a specific URL path.

        Args:
            route (Routes): The HTTP route configuration.

        Returns:
            None

        Example:
            ```python
            route = Routes("/home", home_handler, methods=["GET", "POST"])
            app.add_route(route)
            ```
        """
        
        self.router.add_route(route)
        
        
    
    def add_exception_handler(
        self,
        exc_class_or_status_code: Union[typing.Type[Exception], int],
        handler: HandlerType,
    ) -> None:
        self.exceptions_handler.add_exception_handler(exc_class_or_status_code, handler)
        
        

    
    def url_for(self, _name: str, **path_params: Any) -> URLPath:
        return self.router.url_for(_name,**path_params)