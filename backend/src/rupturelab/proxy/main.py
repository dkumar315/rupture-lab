from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx2
from fastapi import FastAPI

from rupturelab.config import get_settings
from rupturelab.faults.engine import FaultEngine
from rupturelab.proxy.admin import router as admin_router
from rupturelab.proxy.routes import router as proxy_router


def create_proxy_app(
    target_url: str | None = None,
    transport: httpx2.AsyncBaseTransport | None = None,
    fault_engine: FaultEngine | None = None,
) -> FastAPI:
    settings = get_settings()
    upstream_url = target_url or settings.target_url
    engine = fault_engine or FaultEngine()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.fault_engine = engine

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

    # RuptureLab reserves this namespace for proxy control.
    app.include_router(admin_router)
    app.include_router(proxy_router)

    return app


app = create_proxy_app()
