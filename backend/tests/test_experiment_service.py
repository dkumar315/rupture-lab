import asyncio
from uuid import UUID, uuid4

import pytest

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

    async def run(self, spec: ExperimentSpec) -> ExperimentResult:
        assert spec == self.result.spec
        return self.result


class BlockingRunner:
    def __init__(self, result: ExperimentResult) -> None:
        self.result = result
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def run(self, spec: ExperimentSpec) -> ExperimentResult:
        assert spec == self.result.spec
        self.started.set()
        await self.release.wait()
        return self.result


class RecordingStore:
    def __init__(self) -> None:
        self.saved: list[ExperimentResult] = []
        self.summary_calls: list[tuple[int, int]] = []
        self.result: ExperimentResult | None = None

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
