from nexios import get_application
from nexios.plugins import FileRouterPlugin

app = get_application()

FileRouterPlugin(app, config={"root": "routes"})
