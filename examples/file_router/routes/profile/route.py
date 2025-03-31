from multiprocessing import Value
from typing import Callable

from nexios.http import Request, Response


async def get(req: Request, res: Response):
    print("hello, world!")
    return res.json({"ok": True})


async def get_middleware(req: Request, res: Response, next: Callable):
    print(f"Received request: {req.method} {req.path}")
    await next()


async def post(req: Request, res: Response):
    print("hello, world!")
    return res.json({"ok": True})
