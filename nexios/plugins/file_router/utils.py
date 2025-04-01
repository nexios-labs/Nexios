from typing import Optional, Dict, List, Any, Type

from nexios.openapi.models import Parameter
from pydantic import BaseModel


def mark_as_route(
    path: str,
    methods: List[str] = ["get", "post", "patch", "put", "delete"],
    name: Optional[str] = None,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    responses: Optional[Dict[int, Any]] = None,
    request_model: Optional[Type[BaseModel]] = None,
    middlewares: List[Any] = [],
    tags: Optional[List[str]] = None,
    security: Optional[List[Dict[str, List[str]]]] = None,
    operation_id: Optional[str] = None,
    deprecated: bool = False,
    parameters: List[Parameter] = [],
):
    def decorator(func):
        # Use setattr to set attributes dynamically
        setattr(func, "_is_route", True)
        setattr(func, "_path", path)
        setattr(func, "_allowed_methods", [method.lower() for method in methods])
        setattr(func, "_name", name or func.__name__)
        setattr(func, "_summary", summary or "")
        setattr(func, "_description", description or "")
        setattr(func, "_responses", responses or {})
        setattr(func, "_request_model", request_model)
        setattr(func, "_middlewares", middlewares)
        setattr(func, "_tags", tags or [])
        setattr(func, "_security", security or [])
        setattr(func, "_operation_id", operation_id or func.__name__)
        setattr(func, "_deprecated", deprecated)
        setattr(func, "_parameters", parameters)

        return func

    return decorator
