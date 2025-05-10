import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(BASE_DIR))

from typing import Any, Dict

from nexios import get_application
from nexios.plugins.rpc import RpcError, RpcPlugin
from nexios.plugins.rpc.registry import get_registry

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
async def get_user(user_id: int) -> Dict[str, Any]:
    """Get user information."""
    # This would typically be a database query
    users = {
        1: {"id": 1, "name": "Alice", "email": "alice@example.com"},
        2: {"id": 2, "name": "Bob", "email": "bob@example.com"},
    }
    if user_id not in users:
        raise RpcError(404, "User not found", {"user_id": user_id})
    return users[user_id]


app = get_application()

RpcPlugin(app)
