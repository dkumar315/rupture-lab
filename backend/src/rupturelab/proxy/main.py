from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx2
from fastapi import FastAPI

from rupturelab.config import get_settings
from rupturelab.proxy.routes import router


def create_proxy_app(
    target_url: str | None = None,
    transport: httpx2.AsyncBaseTransport | None = None,
) -> FastAPI:
    settings = get_settings()
    upstream_url = target_url or settings.target_url

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.upstream_client = httpx2.AsyncClient(
            base_url=f"{upstream_url.rstrip('/')}/",
            timeout=settings.proxy_timeout_seconds,
            follow_redirects=False,
            transport=transport,
        )

        try:
            yield
        finally:
            await app.state.upstream_client.aclose()

    app = FastAPI(
        title="RuptureLab Proxy",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    app.include_router(router)

    return app


app = create_proxy_app()
