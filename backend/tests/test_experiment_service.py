import asyncio
from uuid import UUID, uuid4

import pytest

from rupturelab.experiments.events import (
    ExperimentEventBroker,
    ExperimentEventPublisher,
)
from rupturelab.experiments.models import (
    ExperimentResult,
    ExperimentSpec,
    ExperimentSummary,
)
from rupturelab.experiments.service import (
    ExperimentBusyError,
    ExperimentService,
)
from rupturelab.faults.models import FaultProfile


def experiment_spec() -> ExperimentSpec:
    return ExperimentSpec(
        name="service-experiment",
        path="/demo/products",
        requests_per_phase=1,
        fault=FaultProfile(
            enabled=True,
            path_prefix="/demo/products",
            methods=["GET"],
            error_status=503,
        ),
    )


def experiment_result(spec: ExperimentSpec) -> ExperimentResult:
    return ExperimentResult(
        experiment_id=str(uuid4()),
        name=spec.name,
        started_at="2026-09-11T06:00:00+00:00",
        spec=spec,
        phases=[],
    )


class ImmediateRunner:
    def __init__(self, result: ExperimentResult) -> None:
        self.result = result

    async def ready(self) -> bool:
        return True

    async def run(
        self,
        spec: ExperimentSpec,
        *,
        experiment_id: UUID | None = None,
        publisher: ExperimentEventPublisher | None = None,
    ) -> ExperimentResult:
        assert spec == self.result.spec
        del publisher
        return self.result.model_copy(
            update={
                "experiment_id": str(experiment_id)
                if experiment_id is not None
                else self.result.experiment_id
            }
        )


class BlockingRunner:
    def __init__(self, result: ExperimentResult) -> None:
        self.result = result
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def ready(self) -> bool:
        return True

    async def run(
        self,
        spec: ExperimentSpec,
        *,
        experiment_id: UUID | None = None,
        publisher: ExperimentEventPublisher | None = None,
    ) -> ExperimentResult:
        assert spec == self.result.spec
        del publisher
        self.started.set()
        await self.release.wait()
        return self.result.model_copy(
            update={
                "experiment_id": str(experiment_id)
                if experiment_id is not None
                else self.result.experiment_id
            }
        )


class RecordingStore:
    def __init__(self) -> None:
        self.saved: list[ExperimentResult] = []
        self.summary_calls: list[tuple[int, int]] = []
        self.result: ExperimentResult | None = None

    async def ready(self) -> bool:
        return True

    async def save(self, result: ExperimentResult) -> None:
        self.saved.append(result)
        self.result = result

    async def list_summaries(
        self,
        *,
        limit: int,
        offset: int,
    ) -> list[ExperimentSummary]:
        self.summary_calls.append((limit, offset))
        return []

    async def get(self, experiment_id: UUID) -> ExperimentResult | None:
        if self.result is not None and UUID(self.result.experiment_id) == experiment_id:
            return self.result

        return None


def test_service_reports_dependency_readiness() -> None:
    class UnreadyRunner(ImmediateRunner):
        async def ready(self) -> bool:
            return False

    class UnreadyStore(RecordingStore):
        async def ready(self) -> bool:
            return False

    async def exercise() -> None:
        spec = experiment_spec()
        result = experiment_result(spec)

        ready_service = ExperimentService(ImmediateRunner(result), RecordingStore())
        assert await ready_service.readiness() == {
            "database": True,
            "proxy": True,
        }

        unready_service = ExperimentService(UnreadyRunner(result), UnreadyStore())
        assert await unready_service.readiness() == {
            "database": False,
            "proxy": False,
        }

    asyncio.run(exercise())


def test_service_persists_completed_experiment() -> None:
    async def exercise() -> None:
        spec = experiment_spec()
        result = experiment_result(spec)
        store = RecordingStore()
        service = ExperimentService(ImmediateRunner(result), store)

        returned = await service.run(spec)

        assert returned == result
        assert store.saved == [result]

    asyncio.run(exercise())


def test_service_rejects_overlapping_experiment() -> None:
    async def exercise() -> None:
        spec = experiment_spec()
        result = experiment_result(spec)
        runner = BlockingRunner(result)
        store = RecordingStore()
        service = ExperimentService(runner, store)

        first_run = asyncio.create_task(service.run(spec))
        await runner.started.wait()

        with pytest.raises(
            ExperimentBusyError,
            match="Another experiment is already running",
        ):
            await service.run(spec)

        runner.release.set()
        assert await first_run == result
        assert store.saved == [result]

    asyncio.run(exercise())


def test_service_delegates_history_reads() -> None:
    async def exercise() -> None:
        spec = experiment_spec()
        result = experiment_result(spec)
        store = RecordingStore()
        store.result = result
        service = ExperimentService(ImmediateRunner(result), store)
        experiment_id = UUID(result.experiment_id)

        assert await service.list_summaries(limit=25, offset=5) == []
        assert store.summary_calls == [(25, 5)]
        assert await service.get(experiment_id) == result
        assert await service.get(uuid4()) is None

    asyncio.run(exercise())


def test_service_starts_background_experiment_and_publishes_terminal_event() -> None:
    async def exercise() -> None:
        spec = experiment_spec()
        result = experiment_result(spec)
        store = RecordingStore()
        service = ExperimentService(ImmediateRunner(result), store)

        started = await service.start(spec)
        experiment_id = UUID(started.experiment_id)

        assert started.name == spec.name
        assert service.has_event_stream(experiment_id) is True

        cursor = 0
        event_types: list[str] = []

        while True:
            read = await service.read_event(
                experiment_id,
                after_sequence=cursor,
                timeout_seconds=0.1,
            )
            assert read.event is not None
            cursor = read.event.sequence
            event_types.append(read.event.type)

            if read.terminal:
                break

        assert event_types == ["experiment.started", "experiment.completed"]
        assert len(store.saved) == 1
        assert store.saved[0].experiment_id == started.experiment_id
        await service.close()

    asyncio.run(exercise())


def test_service_rejects_overlapping_background_experiment() -> None:
    async def exercise() -> None:
        spec = experiment_spec()
        result = experiment_result(spec)
        runner = BlockingRunner(result)
        service = ExperimentService(runner, RecordingStore())

        await service.start(spec)
        await runner.started.wait()

        with pytest.raises(
            ExperimentBusyError,
            match="Another experiment is already running",
        ):
            await service.start(spec)

        runner.release.set()
        await asyncio.sleep(0)
        await service.close()

    asyncio.run(exercise())


def test_service_close_cancels_running_background_experiment() -> None:
    async def exercise() -> None:
        spec = experiment_spec()
        result = experiment_result(spec)
        runner = BlockingRunner(result)
        service = ExperimentService(runner, RecordingStore())

        started = await service.start(spec)
        await runner.started.wait()
        await service.close()

        cursor = 0
        event_types: list[str] = []
        messages: list[str | None] = []

        while True:
            read = await service.read_event(
                UUID(started.experiment_id),
                after_sequence=cursor,
                timeout_seconds=0.1,
            )
            assert read.event is not None
            cursor = read.event.sequence
            event_types.append(read.event.type)
            messages.append(read.event.message)
            if read.terminal:
                break

        assert event_types == ["experiment.started", "experiment.failed"]
        assert messages[-1] == "Experiment cancelled"

    asyncio.run(exercise())


class FailingRunner:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def ready(self) -> bool:
        return True

    async def run(
        self,
        spec: ExperimentSpec,
        *,
        experiment_id: UUID | None = None,
        publisher: ExperimentEventPublisher | None = None,
    ) -> ExperimentResult:
        del spec, experiment_id, publisher
        raise self.error


class RejectingBroker(ExperimentEventBroker):
    def create(self, experiment_id: UUID) -> ExperimentEventPublisher:
        del experiment_id
        raise RuntimeError("broker unavailable")


def test_service_publishes_background_failures() -> None:
    async def collect_message(error: Exception) -> str | None:
        spec = experiment_spec()
        service = ExperimentService(FailingRunner(error), RecordingStore())
        started = await service.start(spec)
        experiment_id = UUID(started.experiment_id)
        cursor = 0

        while True:
            read = await service.read_event(
                experiment_id,
                after_sequence=cursor,
                timeout_seconds=0.1,
            )
            assert read.event is not None
            cursor = read.event.sequence
            if read.terminal:
                return read.event.message

    async def exercise() -> None:
        from rupturelab.experiments.runner import ExperimentControlError

        assert await collect_message(ExperimentControlError("proxy failed")) == "proxy failed"
        assert await collect_message(RuntimeError("unexpected")) == (
            "Experiment failed unexpectedly"
        )

    asyncio.run(exercise())


def test_service_releases_lock_when_event_stream_creation_fails() -> None:
    async def exercise() -> None:
        spec = experiment_spec()
        result = experiment_result(spec)
        store = RecordingStore()
        service = ExperimentService(
            ImmediateRunner(result),
            store,
            event_broker=RejectingBroker(),
        )

        with pytest.raises(RuntimeError, match="broker unavailable"):
            await service.start(spec)

        assert await service.run(spec) == result
        assert store.saved == [result]

    asyncio.run(exercise())
