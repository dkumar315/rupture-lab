import asyncio
from typing import Protocol
from uuid import UUID, uuid4

from rupturelab.experiments.events import (
    EventRead,
    ExperimentEventBroker,
    ExperimentEventPublisher,
)
from rupturelab.experiments.models import (
    ExperimentResult,
    ExperimentSpec,
    ExperimentStart,
    ExperimentSummary,
)
from rupturelab.experiments.runner import ExperimentControlError


class ExperimentExecutor(Protocol):
    async def ready(self) -> bool: ...

    async def run(
        self,
        spec: ExperimentSpec,
        *,
        experiment_id: UUID | None = None,
        publisher: ExperimentEventPublisher | None = None,
    ) -> ExperimentResult: ...


class ExperimentStore(Protocol):
    async def ready(self) -> bool: ...

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
        *,
        event_broker: ExperimentEventBroker | None = None,
    ) -> None:
        self._runner = runner
        self._store = store
        self._run_lock = asyncio.Lock()
        self._event_broker = event_broker or ExperimentEventBroker()
        self._tasks: set[asyncio.Task[None]] = set()

    async def readiness(self) -> dict[str, bool]:
        proxy_ready, database_ready = await asyncio.gather(
            self._runner.ready(),
            self._store.ready(),
        )
        return {
            "database": database_ready,
            "proxy": proxy_ready,
        }

    async def run(self, spec: ExperimentSpec) -> ExperimentResult:
        if self._run_lock.locked():
            raise ExperimentBusyError("Another experiment is already running")

        async with self._run_lock:
            result = await self._runner.run(spec)
            await self._store.save(result)

        return result

    async def start(self, spec: ExperimentSpec) -> ExperimentStart:
        if self._run_lock.locked():
            raise ExperimentBusyError("Another experiment is already running")

        await self._run_lock.acquire()
        experiment_id = uuid4()

        try:
            publisher = self._event_broker.create(experiment_id)
            task = asyncio.create_task(
                self._run_background(
                    experiment_id,
                    spec,
                    publisher,
                )
            )
        except BaseException:
            self._run_lock.release()
            raise

        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

        return ExperimentStart(
            experiment_id=str(experiment_id),
            name=spec.name,
        )

    def has_event_stream(self, experiment_id: UUID) -> bool:
        return self._event_broker.contains(experiment_id)

    async def read_event(
        self,
        experiment_id: UUID,
        *,
        after_sequence: int,
        timeout_seconds: float,
    ) -> EventRead:
        return await self._event_broker.read(
            experiment_id,
            after_sequence=after_sequence,
            timeout_seconds=timeout_seconds,
        )

    async def close(self) -> None:
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

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

    async def _run_background(
        self,
        experiment_id: UUID,
        spec: ExperimentSpec,
        publisher: ExperimentEventPublisher,
    ) -> None:
        try:
            await publisher.experiment_started(spec)
            result = await self._runner.run(
                spec,
                experiment_id=experiment_id,
                publisher=publisher,
            )
            await self._store.save(result)
            await publisher.experiment_completed(result)
        except asyncio.CancelledError:
            await publisher.experiment_failed("Experiment cancelled")
            raise
        except ExperimentControlError as exc:
            await publisher.experiment_failed(str(exc))
        except Exception:
            await publisher.experiment_failed("Experiment failed unexpectedly")
        finally:
            self._run_lock.release()
