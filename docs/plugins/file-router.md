# FileRouterPlugin

`FileRouterPlugin` is a plugin for the Nexios framework that automatically discovers and registers routes from Python files located in a specified directory. It scans for `route.py` files and maps HTTP methods (`GET`, `POST`, `PATCH`, `PUT`, `DELETE`) to corresponding handler functions.

## Usage

### Basic Example

```python
from nexios import get_application
from nexios.plugins import FileRouterPlugin

app = get_application()
FileRouterPlugin(app, config={"root": "./routes"})
```

When the plugin is instantiated, it will:

1. Recursively scan the `./routes` directory.
2. Find files named `route.py`.
3. Import them dynamically.
4. Register any functions named `get`, `post`, `patch`, `put`, or `delete` as HTTP handlers.

## Route File Structure

Each `route.py` file should define handler functions corresponding to HTTP methods. Example:

```python
# routes/users/route.py

def get():
    return {"message": "GET request received"}

def post():
    return {"message": "POST request received"}
```

This will automatically create:

- `GET /users`
- `POST /users`

## Configuration

The plugin accepts a configuration dictionary with the following key:

| Key    | Type  | Default Value | Description                            |
| ------ | ----- | ------------- | -------------------------------------- |
| `root` | `str` | `"./routes"`  | The directory to scan for route files. |

## How It Works

1. The plugin is initialized with an `app` instance and a `config` dictionary.
2. It scans the `root` directory using `os.walk()`.
3. It locates all `route.py` files and processes them dynamically.
4. `importlib.import_module()` loads the route file as a module.
5. Functions named `get`, `post`, `patch`, `put`, or `delete` are mapped to HTTP methods.
6. Routes are registered with the application via `self.app.add_route()`.
