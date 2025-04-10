from typing import Callable, Dict, Optional

from .exceptions import RpcMethodNotFound


class RpcRegistry:
    """Registry for RPC methods."""

    # Class variable to store the singleton instance
    _instance = None

    def __new__(cls):
        """Implement singleton pattern using __new__"""
        if cls._instance is None:
            cls._instance = super(RpcRegistry, cls).__new__(cls)
            # Initialize the instance attributes
            cls._instance.methods = {}
        return cls._instance

    def register(self, name: Optional[str] = None) -> Callable:
        """Decorator to register a function as an RPC method."""

        def decorator(func: Callable) -> Callable:
            method_name = name if name else func.__name__
            self.methods[method_name] = func
            return func

        return decorator

    def get_method(self, name: str) -> Callable:
        """Get a registered method by name."""
        if name not in self.methods:
            raise RpcMethodNotFound(name)
        return self.methods[name]


# Function to get the singleton registry instance
def get_registry() -> RpcRegistry:
    """
    Get the singleton RpcRegistry instance.
    This ensures only one registry exists throughout the application.

    Returns:
        RpcRegistry: The singleton registry instance
    """
    return RpcRegistry()
