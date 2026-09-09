import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

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


def test_database_base_starts_with_empty_metadata() -> None:
    assert not Base.metadata.tables
