import inspect
from typing import Any, Callable, Dict, TypedDict

from nexios.application import NexiosApp
from nexios.http import Request, Response
from nexios.routing import Routes

from .exceptions import RpcError, RpcInvalidParams, RpcInvalidRequest
from .registry import RpcRegistry, get_registry


class RpcPluginConfig(TypedDict):
    path_prefix: str


class RpcPlugin:
    """RPC server built on Starlette."""

    app: NexiosApp
    config: RpcPluginConfig
    registry: RpcRegistry

    def __init__(
        self,
        app: NexiosApp,
        config: RpcPluginConfig = {"path_prefix": "/rpc"},
    ):
        self.app = app
        self.config = config
        self.registry = get_registry()

        self._setup()

    def _setup(self):
        self.app.add_route(
            Routes(self.config["path_prefix"], self.handle_rpc, methods=["POST"])
        )

    async def handle_rpc(self, req: Request, res: Response):
        """Handle RPC requests."""
        try:
            # Parse the request
            data = await req.json

            # Validate the request
            if not isinstance(data, dict):
                raise RpcInvalidRequest("Request must be a JSON object")

            method_name = data.get("method")
            if not method_name or not isinstance(method_name, str):
                raise RpcInvalidRequest("Method name must be a string")

            params = data.get("params", {})
            if not isinstance(params, (dict, list)):
                raise RpcInvalidRequest("Params must be an object or array")

            request_id = data.get("id")
            if request_id is not None and not isinstance(request_id, (str, int)):
                raise RpcInvalidRequest("Id must be a string or number")

            # Get the method
            method = self.registry.get_method(method_name)

            # Call the method
            result = await self._call_method(method, params)

            return res.json({"jsonrpc": "2.0", "result": result, "id": request_id})

        except RpcError as e:
            return res.json(
                {
                    "jsonrpc": "2.0",
                    "error": {"code": e.code, "message": e.message, "data": e.data},
                    "id": data.get("id") if isinstance(data, dict) else None,
                }
            )

        except Exception as e:
            return res.json(
                {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                        "data": str(e),
                    },
                    "id": data.get("id") if isinstance(data, dict) else None,
                }
            )

    async def _call_method(self, method: Callable, params: Dict[str, Any]) -> Any:
        """Call a method with the given parameters."""
        signature = inspect.signature(method)

        # Check if the method is async
        is_async = inspect.iscoroutinefunction(method)

        # Prepare the arguments
        if isinstance(params, dict):
            # Named parameters
            kwargs = params
            args = []
        else:
            # Positional parameters
            args = params
            kwargs = {}

        try:
            # Bind the arguments to the method signature
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()

            # Call the method
            if is_async:
                return await method(*bound.args, **bound.kwargs)
            else:
                return method(*bound.args, **bound.kwargs)
        except TypeError as e:
            raise RpcInvalidParams(str(e))
