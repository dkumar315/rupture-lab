import asyncio
from typing import Protocol
from uuid import UUID

from rupturelab.experiments.models import (
    ExperimentResult,
    ExperimentSpec,
    ExperimentSummary,
)


class ExperimentExecutor(Protocol):
    async def run(self, spec: ExperimentSpec) -> ExperimentResult: ...


class ExperimentStore(Protocol):
    async def save(self, result: ExperimentResult) -> None: ...

    async def list_summaries(
        self,
        *,
        limit: int,
        offset: int,
    ) -> list[ExperimentSummary]: ...

    async def get(self, experiment_id: UUID) -> ExperimentResult | None: ...


class ExperimentBusyError(RuntimeError):
    pass


class ExperimentService:
    def __init__(
        self,
        runner: ExperimentExecutor,
        store: ExperimentStore,
    ) -> None:
        self._runner = runner
        self._store = store
        self._run_lock = asyncio.Lock()

    async def run(self, spec: ExperimentSpec) -> ExperimentResult:
        if self._run_lock.locked():
            raise ExperimentBusyError("Another experiment is already running")

        async with self._run_lock:
            result = await self._runner.run(spec)
            await self._store.save(result)

        return result

    async def list_summaries(
        self,
        *,
        limit: int,
        offset: int,
    ) -> list[ExperimentSummary]:
        return await self._store.list_summaries(
            limit=limit,
            offset=offset,
        )

    async def get(self, experiment_id: UUID) -> ExperimentResult | None:
        return await self._store.get(experiment_id)
