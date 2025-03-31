import os
from pathlib import Path
from typing import TypedDict

from nexios.application import NexiosApp
from nexios.http import Request, Response
from nexios.routing import Routes


class StaticFilePluginConfig(TypedDict):
    url: str
    file_dir: str


class StaticFilePlugin:
    """
    from nexios import get_application
    from nexios.plugins import StaticFilePluginPlugin

    app = get_application()

    StaticFilePluginPlugin(app, config={"url": "/static", "file_dir": "./"})
    """

    app: NexiosApp
    config: StaticFilePluginConfig

    def __init__(self, app, config: StaticFilePluginConfig):
        self.app = app
        self.config = config

        self._setup()

    def _setup(self):
        static_directory = Path(self.config["file_dir"])

        async def handler(req: Request, res: Response):
            try:
                path = static_directory.joinpath(req.path_params.path)
                return res.file(path, str(path).split("/")[-1])
            except Exception as e:
                # TODO: handle error
                return res.json({"error": e}, 500)

        self.app.add_route(
            Routes(
                os.path.join(self.config["url"], "{path:path}"),
                handler,
                methods=["GET"],
            )
        )
