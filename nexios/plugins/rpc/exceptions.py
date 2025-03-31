from typing import Any, Optional


class RpcError(Exception):
    """Base class for RPC errors."""

    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        self.code = code
        self.message = message
        self.data = data

        super().__init__(message)


class RpcMethodNotFound(RpcError):
    """Raised when the requested method is not found."""

    def __init__(self, method_name: str):
        super().__init__(code=-32601, message=f"Method not found: {method_name}")


class RpcInvalidParams(RpcError):
    """Raised when invalid parameters are provided."""

    def __init__(self, message: str = "Invalid parameters"):
        super().__init__(code=-32602, message=message)


class RpcInvalidRequest(RpcError):
    """Raised when the request is invalid."""

    def __init__(self, message: str = "Invalid request"):
        super().__init__(code=-32600, message=message)


class RpcClientError(Exception):
    """Exception raised for RPC client errors."""

    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        """
        Initialize the RPC client error.

        Args:
            code: The error code
            message: The error message
            data: Additional error data (optional)
        """
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"[{code}] {message}")
