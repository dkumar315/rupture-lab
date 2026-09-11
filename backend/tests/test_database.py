import asyncio

from sqlalchemy import inspect
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession

from rupturelab.db import models as db_models
from rupturelab.db.base import Base
from rupturelab.db.session import (
    create_database_engine,
    create_session_factory,
)


def test_database_engine_and_session_factory() -> None:
    async def exercise() -> None:
        engine = create_database_engine("sqlite+aiosqlite:///:memory:")
        session_factory = create_session_factory(engine)

        async with session_factory() as session:
            assert isinstance(session, AsyncSession)

        await engine.dispose()

    asyncio.run(exercise())


def test_database_metadata_contains_history_tables() -> None:
    assert set(Base.metadata.tables) == {
        "experiment_runs",
        "phase_results",
        "request_measurements",
        "contract_checks",
    }

    assert db_models.ExperimentRunRecord.__tablename__ == "experiment_runs"
    assert db_models.PhaseResultRecord.__tablename__ == "phase_results"
    assert db_models.RequestMeasurementRecord.__tablename__ == "request_measurements"
    assert db_models.ContractCheckRecord.__tablename__ == "contract_checks"


def test_database_history_schema_can_be_created() -> None:
    def table_names(connection: Connection) -> set[str]:
        return set(inspect(connection).get_table_names())

    async def exercise() -> None:
        engine = create_database_engine("sqlite+aiosqlite:///:memory:")

        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

            assert await connection.run_sync(table_names) == {
                "experiment_runs",
                "phase_results",
                "request_measurements",
                "contract_checks",
            }

            await connection.run_sync(Base.metadata.drop_all)

        await engine.dispose()

    asyncio.run(exercise())


def test_history_tables_reference_experiment_runs() -> None:
    for table_name in (
        "phase_results",
        "request_measurements",
        "contract_checks",
    ):
        table = Base.metadata.tables[table_name]
        foreign_keys = table.c.experiment_id.foreign_keys

        assert len(foreign_keys) == 1
        assert next(iter(foreign_keys)).target_fullname == "experiment_runs.id"


def test_app_lifespan_builds_database_repository() -> None:
    from fastapi.testclient import TestClient

    from rupturelab.main import create_app

    app = create_app(
        proxy_url="http://proxy",
        database_url="sqlite+aiosqlite:///:memory:",
    )

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
