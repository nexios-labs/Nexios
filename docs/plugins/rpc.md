# Nexios RPC Plugin (JSON-RPC 2.0)

A lightweight, easy-to-use RPC (Remote Procedure Call) plugin for Nexios applications.

## Table of Contents

- [Quick Start](#quick-start)
- [Core Components](#core-components)
  - [RPC Registry](#rpc-registry)
  - [RPC Plugin](#rpc-plugin)
  - [RPC Client](#rpc-client)
- [API Reference](#api-reference)
  - [Server-side API](#server-side-api)
  - [Client-side API](#client-side-api)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [Best Practices](#best-practices)

## Quick Start

### Server-side

```python
from nexios.application import NexiosApp
from nexios.plugins.rpc import RpcError, RpcPlugin
from nexios.plugins.rpc.registry import get_registry

# Create your Nexios application
app = NexiosApp()

# Set up the RPC plugin
rpc = RpcPlugin(app, {"path_prefix": "/api/rpc"})

# Register RPC methods
registry = get_registry()

@registry.register()
async def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

@registry.register(name="subtract")
def sub(a: int, b: int) -> int:
    """Subtract b from a."""
    return a - b

@registry.register()
async def get_user(user_id: int) -> dict:
    """Get user information."""
    # This would typically be a database query
    users = {
        1: {"id": 1, "name": "Alice", "email": "alice@example.com"},
        2: {"id": 2, "name": "Bob", "email": "bob@example.com"}
    }
    if user_id not in users:
        from nexios_rpc.exceptions import RpcError
        raise RpcError(404, "User not found", {"user_id": user_id})
    return users[user_id]

# Run the application
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

### Client-side

```python
from nexios_rpc.client import RpcClient

# Create an RPC client
client = RpcClient("http://localhost:8000/api/rpc")

# Call RPC methods
result = client.add(a=5, b=3)  # 8
user = client.get_user(user_id=1)  # {"id": 1, "name": "Alice", "email": "alice@example.com"}

# Alternative call syntax
result = client.call("add", {"a": 5, "b": 3})  # 8
```

## Core Components

### RPC Registry

The `RpcRegistry` follows the singleton pattern to ensure that only a single registry exists throughout your application. This provides a central place to register all your RPC methods.

```python
from nexios.plugins.rpc.registry import get_registry

registry = get_registry()

@registry.register()  # Uses function name as method name
async def my_method(param1: str, param2: int) -> dict:
    return {"param1": param1, "param2": param2}

@registry.register(name="custom_name")  # Custom method name
def another_method(value: float) -> float:
    return value * 2
```

### RPC Plugin

The `RpcPlugin` integrates with your Nexios application to handle RPC requests. It automatically registers an endpoint that processes RPC calls according to the JSON-RPC 2.0 specification.

```python
from nexios.application import NexiosApp
from nexios.plugins.rpc import RpcError, RpcPlugin

app = NexiosApp()
rpc = RpcPlugin(app, {
    "path_prefix": "/api/rpc"  # Default is "/rpc"
})
```

### RPC Client

The `RpcClient` provides a clean interface for making RPC calls to your server without requiring any external dependencies.

```python
from nexios.plugins.rpc.client import RpcClient

client = RpcClient("http://localhost:8000/api/rpc")

# Method 1: Attribute-style with named parameters
result = client.method_name(param1="value1", param2="value2")

# Method 2: Attribute-style with positional parameters
result = client.method_name("value1", "value2")

# Method 3: Explicit call with named parameters
result = client.call("method_name", {"param1": "value1", "param2": "value2"})

# Method 4: Explicit call with positional parameters
result = client.call("method_name", ["value1", "value2"])
```

## API Reference

### Server-side API

#### `get_registry()`

Returns the singleton instance of `RpcRegistry`.

#### `RpcRegistry`

- `register(name: Optional[str] = None)`: Decorator to register a function as an RPC method
- `get_method(name: str)`: Get a registered method by name

#### `RpcPlugin`

- `__init__(app: NexiosApp, config: RpcPluginConfig = {"path_prefix": "/rpc"})`: Initialize the plugin
- `handle_rpc(req: Request, res: Response)`: Handle RPC requests

#### Exceptions

- `RpcError(code: int, message: str, data: Optional[Any] = None)`: Base class for RPC errors
- `RpcMethodNotFound(name: str)`: Raised when the requested method is not found
- `RpcInvalidParams(message: str = "Invalid parameters")`: Raised when invalid parameters are provided
- `RpcInvalidRequest(message: str = "Invalid request")`: Raised when the request is invalid

### Client-side API

#### `RpcClient`

- `__init__(base_url: str)`: Initialize the client with the RPC server URL
- `call(method: str, params: Union[Dict[str, Any], List[Any]] = None)`: Explicitly call an RPC method
- `__getattr__(method_name: str)`: Magic method that enables attribute-style calls

#### `RpcClientError`

- `__init__(code: int, message: str, data: Optional[Any] = None)`: Initialize a client error

## Error Handling

The framework follows the JSON-RPC 2.0 specification for error handling. Common error codes include:

- `-32600`: Invalid request
- `-32601`: Method not found
- `-32602`: Invalid params
- `-32603`: Internal error

Custom error codes can be used for application-specific errors.

```python
from nexios_rpc.exceptions import RpcError

@registry.register()
async def withdraw(account_id: str, amount: float) -> dict:
    if amount <= 0:
        raise RpcError(400, "Invalid amount", {"amount": amount})

    account = get_account(account_id)
    if account.balance < amount:
        raise RpcError(
            403,
            "Insufficient funds",
            {"balance": account.balance, "requested": amount}
        )

    # Process withdrawal
    return {"success": True, "new_balance": account.balance - amount}
```

On the client side:

```python
try:
    result = client.withdraw(account_id="123", amount=-50)
except RpcClientError as e:
    print(f"Error {e.code}: {e.message}")
    print(f"Additional data: {e.data}")
```

## Examples

### Authentication Example

```python
from functools import wraps
from nexios.plugins.rpc.registry import get_registry
from nexios.plugins.rpc import RpcError

registry = get_registry()

def require_auth(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Get context (can be passed as part of the request)
        context = kwargs.pop('context', {})
        if 'token' not in context or not validate_token(context['token']):
            raise RpcError(401, "Unauthorized", {"message": "Valid token required"})
        return await func(*args, **kwargs)
    return wrapper

@registry.register()
@require_auth
async def protected_method(param1: str) -> dict:
    # Only called if authentication passes
    return {"result": "Success", "param": param1}
```

### Database Operation Example

```python
from nexios.plugins.rpc.registry import get_registry
from nexios.plugins.rpc import RpcError
import asyncpg

registry = get_registry()

@registry.register()
async def get_products(category: str = None, limit: int = 10, offset: int = 0) -> list:
    try:
        conn = await asyncpg.connect("postgresql://user:password@localhost/database")

        query = "SELECT * FROM products"
        params = []

        if category:
            query += " WHERE category = $1"
            params.append(category)

        query += f" LIMIT {limit} OFFSET {offset}"

        rows = await conn.fetch(query, *params)
        products = [dict(row) for row in rows]

        await conn.close()
        return products
    except Exception as e:
        raise RpcError(500, "Database error", {"message": str(e)})
```

## Best Practices

1. **Method Naming**: Use descriptive, namespaced method names to avoid collisions (e.g., `user.get`, `user.update`).

2. **Input Validation**: Validate inputs early to prevent errors deeper in your application.

3. **Type Annotations**: Use Python type annotations to document parameter types and return values.

4. **Error Handling**: Return meaningful error messages and appropriate error codes.

5. **Authentication**: Implement authentication middleware to protect sensitive RPC methods.

6. **Documentation**: Document each RPC method with docstrings that describe parameters and return values.

7. **Testing**: Write unit tests for your RPC methods to ensure they handle various inputs correctly.
