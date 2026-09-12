from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx2
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from rupturelab.api.routes.experiments import router as experiments_router
from rupturelab.api.routes.system import router as system_router
from rupturelab.config import get_settings
from rupturelab.db.repository import ExperimentRepository
from rupturelab.db.session import (
    create_database_engine,
    create_session_factory,
)
from rupturelab.experiments.runner import ExperimentRunner
from rupturelab.experiments.service import (
    ExperimentService,
    ExperimentStore,
)


def create_app(
    proxy_url: str | None = None,
    transport: httpx2.AsyncBaseTransport | None = None,
    database_url: str | None = None,
    experiment_store: ExperimentStore | None = None,
) -> FastAPI:
    settings = get_settings()
    upstream_proxy = proxy_url or settings.proxy_url
    resolved_database_url = database_url or settings.database_url

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.proxy_client = httpx2.AsyncClient(
            base_url=f"{upstream_proxy.rstrip('/')}/",
            timeout=settings.experiment_timeout_seconds,
            transport=transport,
        )

        database_engine: AsyncEngine | None = None
        store = experiment_store

        if store is None:
            database_engine = create_database_engine(resolved_database_url)
            store = ExperimentRepository(create_session_factory(database_engine))

        app.state.experiment_service = ExperimentService(
            ExperimentRunner(app.state.proxy_client),
            store,
        )

        try:
            yield
        finally:
            await app.state.experiment_service.close()
            await app.state.proxy_client.aclose()

            if database_engine is not None:
                await database_engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(system_router)
    app.include_router(experiments_router)

    return app


app = create_app()
