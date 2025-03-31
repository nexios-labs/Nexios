from typing import TypedDict

from nexios.plugins.rpc.registry import get_registry


class Todo(TypedDict):
    id: int
    title: str
    completed: bool


todos: list[Todo] = [
    {
        "id": 1,
        "title": "Implement File Router Plugin",
        "completed": True,
    },
    {
        "id": 2,
        "title": "Implement HTML Router Router",
        "completed": False,
    },
]


registry = get_registry()


@registry.register()
def TodoServiceList(completed: bool = None):
    if completed is None:
        return todos
    return list(filter(lambda t: t["completed"] == completed, todos))


@registry.register()
def TodoServiceCreate(item: Todo):
    item["id"] = len(todos) + 1
    todos.append(item)

    return item


@registry.register()
def TodoServiceGet(id: int):
    return next((t for t in todos if t["id"] == id), None)


@registry.register()
def TodoServiceUpdate(id: int, item: Todo):
    print("item -> ", item)
    for idx, todo in enumerate(todos):
        if todo["id"] == id:
            print(todo)

            todos[idx] = {**todo, **item}

            print(todos[idx])

            return todo
    return None


@registry.register()
def TodoServiceDelete(id: int):
    global todos

    todos = filter(lambda t: t["id"] != id, todos)
