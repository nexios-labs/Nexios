from nexios.http import Request, Response
from nexios.plugins.html import render

from .todo_service import TodoServiceList


@render()
async def get(req: Request, res: Response):
    return {"todos": TodoServiceList()}
