from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx2
from fastapi import FastAPI

from rupturelab.api.routes.experiments import (
    router as experiments_router,
)
from rupturelab.api.routes.system import router as system_router
from rupturelab.config import get_settings


def create_app(
    proxy_url: str | None = None,
    transport: httpx2.AsyncBaseTransport | None = None,
) -> FastAPI:
    settings = get_settings()
    upstream_proxy = proxy_url or settings.proxy_url

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.proxy_client = httpx2.AsyncClient(
            base_url=f"{upstream_proxy.rstrip('/')}/",
            timeout=settings.experiment_timeout_seconds,
            transport=transport,
        )

        try:
            yield
        finally:
            await app.state.proxy_client.aclose()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(system_router)
    app.include_router(experiments_router)

    return app


app = create_app()
