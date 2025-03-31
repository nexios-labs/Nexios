import importlib
import os
from typing import Callable, TypedDict

from nexios.application import NexiosApp
from nexios.http import Request, Response
from nexios.logging import create_logger
from nexios.routing import Routes
from nexios.types import HandlerType

logger = create_logger("nexios")


class FileRouterConfig(TypedDict):
    root: str


class FileRouterPlugin:
    """
    from nexios import get_application
    from nexios.plugins import FileRouterPlugin

    app = get_application()

    FileRouterPlugin(app, config={"root": "./routes"}).setup()
    """

    app: NexiosApp
    config: FileRouterConfig

    def __init__(self, app, config: FileRouterConfig = {"root": "./routes"}):
        self.app = app
        self.config = config

        self._setup()

    def _setup(self):
        for root, _, files in os.walk(self.config["root"]):
            for file in files:
                file_path = os.path.join(root, file)
                if not file_path.endswith("route.py"):
                    continue

                for route in self._build_route(file_path):
                    self.app.add_route(route)

    def _get_path(self, route_file_path: str) -> str:
        path = route_file_path.replace("route.py", "")
        segments = [
            "{%s}" % segment.replace("_", "") if segment.startswith("_") else segment
            for segment in path.split("/")
        ]

        return "/".join(segments)

    def _build_route(self, route_file_path: str) -> list[Routes]:
        handlers: list[Routes] = []
        path = self._get_path(route_file_path.replace(self.config["root"], ""))
        module = importlib.import_module(
            route_file_path.replace("/", ".").replace(".py", "")
        )

        def register_methods_and_middlewares(method: str):
            middlewares: list[Callable[[Request, Response, Callable]]] = []
            middleware_name = "%s_middleware" % method.lower()
            middleware_exists = hasattr(module, middleware_name)
            if middleware_exists:
                middlewares.append(getattr(module, middleware_name))

            method_exists = hasattr(module, method.lower())
            if method_exists:
                logger.debug(
                    "Mapped %s %s -> %s middlewares(s)"
                    % (method, path, len(middlewares))
                )

                handler: HandlerType = getattr(module, method.lower())

                handlers.append(
                    Routes(
                        path,
                        handler,
                        methods=[method],
                        middlewares=middlewares,
                    )
                )

        register_methods_and_middlewares("GET")
        register_methods_and_middlewares("POST")
        register_methods_and_middlewares("PATCH")
        register_methods_and_middlewares("PUT")
        register_methods_and_middlewares("DELETE")

        return handlers
