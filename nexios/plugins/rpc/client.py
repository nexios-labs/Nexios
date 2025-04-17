import json
import urllib.request
from typing import Any, Dict, List, Union

from .exceptions import RpcClientError


class RpcClient:
    """
    A client for the RPC server that doesn't require external packages.
    Uses only standard library modules.
    """

    def __init__(self, base_url: str):
        """
        Initialize the RPC client.

        Args:
            base_url: The base URL of the RPC server, including the path prefix
            (e.g., "http://localhost:8000/rpc")
        """
        self.base_url = base_url
        self.request_id = 0

    def _generate_request_id(self) -> int:
        """Generate a unique request ID."""
        self.request_id += 1
        return self.request_id

    def _make_request(
        self, method: str, params: Union[Dict[str, Any], List[Any]]
    ) -> Dict[str, Any]:
        """
        Make an RPC request to the server.

        Args:
            method: The name of the RPC method to call
            params: The parameters to pass to the method (dict or list)

        Returns:
            The response from the server

        Raises:
            Exception: If there's an error in the response
        """
        # Create the request payload
        request_id = self._generate_request_id()
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id,
        }

        # Convert the payload to JSON
        data = json.dumps(payload).encode("utf-8")

        # Create the request
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        req = urllib.request.Request(
            url=self.base_url, data=data, headers=headers, method="POST"
        )

        # Send the request and get the response
        try:
            with urllib.request.urlopen(req) as response:
                response_data = json.loads(response.read().decode("utf-8"))

                # Check if there's an error in the response
                if "error" in response_data:
                    error = response_data["error"]
                    raise RpcClientError(
                        code=error.get("code", -32603),
                        message=error.get("message", "Unknown error"),
                        data=error.get("data"),
                    )

                # Return the result
                return response_data.get("result")
        except urllib.error.HTTPError as e:
            # Handle HTTP errors
            try:
                error_data = json.loads(e.read().decode("utf-8"))
                if "error" in error_data:
                    error = error_data["error"]
                    raise RpcClientError(
                        code=error.get("code", -32603),
                        message=error.get("message", "Server error"),
                        data=error.get("data"),
                    )
            except json.JSONDecodeError:
                pass

            raise RpcClientError(
                code=-32603, message=f"HTTP error: {e.code} {e.reason}", data=None
            )
        except Exception as e:
            raise RpcClientError(
                code=-32603, message=f"Request error: {str(e)}", data=None
            )

    def __getattr__(self, method_name: str):
        """
        Enable calling RPC methods directly as attributes of the client.

        Example:
            client.add(a=1, b=2)
            client.get_user(user_id=1)
        """

        def method_caller(*args, **kwargs):
            # Determine whether to use positional or named parameters
            if args and kwargs:
                raise ValueError("Cannot mix positional and named parameters")

            params = kwargs if kwargs else list(args)
            return self._make_request(method_name, params)

        return method_caller

    def call(self, method: str, params: Union[Dict[str, Any], List[Any]] = None) -> Any:
        """
        Call an RPC method.

        Args:
            method: The name of the RPC method to call
            params: The parameters to pass to the method (default: None)

        Returns:
            The result of the RPC method call
        """
        if params is None:
            params = {}
        return self._make_request(method, params)
