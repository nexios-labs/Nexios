import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(BASE_DIR))

from nexios.plugins.rpc.client import RpcClient

# Initialize the client with the URL of your RPC server
client = RpcClient("http://localhost:8000/rpc")

# Method 1: Call methods using dot notation
result1 = client.add(a=5, b=3)
user = client.get_user(user_id=1)
print(result1, user)

# Method 2: Call methods using the call() method
result2 = client.call("add", {"a": 5, "b": 3})
user = client.call("get_user", {"user_id": 1})
print(result2, user)


# Method 3: Using positional parameters
result3 = client.add(5, 3)
user = client.get_user(1)
print(result3, user)


# Method 4: Using the call() method with positional parameters
result4 = client.call("add", [5, 3])
result5 = client.call("subtract", [10, 1])
print(result4, result5)
