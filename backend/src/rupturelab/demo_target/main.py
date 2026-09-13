from fastapi import FastAPI

from rupturelab import __version__
from rupturelab.demo_target.routes import router


def create_demo_app() -> FastAPI:
    app = FastAPI(
        title="RuptureLab Demo Target",
        version=__version__,
    )

    app.include_router(router)

    return app


app = create_demo_app()
