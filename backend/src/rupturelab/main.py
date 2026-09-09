from fastapi import FastAPI

from rupturelab.api.routes.system import router as system_router
from rupturelab.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )

    app.include_router(system_router)

    return app


app = create_app()
