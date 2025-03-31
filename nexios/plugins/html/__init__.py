import functools
import inspect
import os
from os.path import exists, getmtime, join
from typing import TypedDict

from jinja2 import BaseLoader, Environment, TemplateNotFound, select_autoescape

from nexios.http import Request, Response
from nexios.logging import create_logger
from nexios.plugins.file_router import FileRouterPlugin

logger = create_logger("nexios")


class Loader(BaseLoader):
    def __init__(self, path: str):
        self.path = path

    def get_source(self, environment, template):
        path = join(self.path, template)
        if not exists(path):
            raise TemplateNotFound(template)
        mtime = getmtime(path)
        with open(path) as f:
            source = f.read()
        return source, path, lambda: mtime == getmtime(path)


class HTMLPluginConfig(TypedDict):
    root: str


class HTMLPlugin(FileRouterPlugin):
    def __init__(self, app, config=...):
        super().__init__(app, config)


def render(template_path: str = "route.html"):
    # Get the module that defined the function
    stack = inspect.stack()
    caller_frame = stack[1]  # The caller's frame
    caller_module = inspect.getmodule(caller_frame[0])
    caller_dir = os.path.dirname(os.path.abspath(caller_module.__file__))

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(req: Request, res: Response, *args, **kwargs):
            ctx = await func(req, res, *args, **kwargs)

            if not isinstance(ctx, dict):
                raise ValueError("The decorated function must return a dictionary.")

            # Setup Jinja2 environment
            env = Environment(loader=Loader(caller_dir), autoescape=select_autoescape())

            # Render the template
            return res.html(env.get_template(template_path).render(**ctx))

        return wrapper

    return decorator
