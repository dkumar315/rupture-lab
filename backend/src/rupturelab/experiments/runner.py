import asyncio
from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID, uuid4

import httpx2

from rupturelab.contracts.evaluator import evaluate_contract
from rupturelab.experiments.events import ExperimentEventPublisher
from rupturelab.experiments.metrics import summarize_phase
from rupturelab.experiments.models import (
    ExperimentResult,
    ExperimentSpec,
    PhaseName,
    PhaseResult,
    RequestMeasurement,
)


class ExperimentControlError(RuntimeError):
    pass


class ExperimentRunner:
    def __init__(self, client: httpx2.AsyncClient) -> None:
        self._client = client

    async def run(
        self,
        spec: ExperimentSpec,
        *,
        experiment_id: UUID | None = None,
        publisher: ExperimentEventPublisher | None = None,
    ) -> ExperimentResult:
        started_at = datetime.now(UTC)
        resolved_experiment_id = experiment_id or uuid4()

        await self._clear_fault()

        baseline = await self._run_phase(
            "baseline",
            spec,
            publisher=publisher,
        )

        await self._configure_fault(spec)

        try:
            fault = await self._run_phase(
                "fault",
                spec,
                publisher=publisher,
            )
        finally:
            await self._clear_fault()

        recovery = await self._run_phase(
            "recovery",
            spec,
            publisher=publisher,
        )

        phases = [baseline, fault, recovery]
        contract_evaluation = (
            evaluate_contract(spec.contract, phases) if spec.contract is not None else None
        )

        if publisher is not None and contract_evaluation is not None:
            await publisher.contract_evaluated(contract_evaluation)

        return ExperimentResult(
            experiment_id=str(resolved_experiment_id),
            name=spec.name,
            started_at=started_at.isoformat(),
            spec=spec,
            phases=phases,
            contract_evaluation=contract_evaluation,
        )

    async def _run_phase(
        self,
        phase: PhaseName,
        spec: ExperimentSpec,
        *,
        publisher: ExperimentEventPublisher | None,
    ) -> PhaseResult:
        measurements: list[RequestMeasurement] = []

        if publisher is not None:
            await publisher.phase_started(phase, spec.requests_per_phase)

        for index in range(spec.requests_per_phase):
            measurement = await self._send_request(spec)
            measurements.append(measurement)

            if publisher is not None:
                await publisher.request_completed(
                    phase,
                    index + 1,
                    spec.requests_per_phase,
                    measurement,
                )

            if spec.interval_ms > 0 and index < spec.requests_per_phase - 1:
                await asyncio.sleep(spec.interval_ms / 1000)

        result = summarize_phase(phase, measurements)

        if publisher is not None:
            await publisher.phase_completed(result)

        return result

    async def _send_request(
        self,
        spec: ExperimentSpec,
    ) -> RequestMeasurement:
        started = perf_counter()

        try:
            response = await self._client.request(
                method=spec.method,
                url=spec.path,
                headers=spec.headers,
                json=spec.body,
            )
        except httpx2.RequestError as exc:
            duration_ms = (perf_counter() - started) * 1000

            return RequestMeasurement(
                status_code=None,
                duration_ms=round(duration_ms, 3),
                successful=False,
                error=type(exc).__name__,
            )

        duration_ms = (perf_counter() - started) * 1000

        return RequestMeasurement(
            status_code=response.status_code,
            duration_ms=round(duration_ms, 3),
            successful=200 <= response.status_code < 400,
            fault=response.headers.get("x-rupturelab-fault"),
        )

    async def _configure_fault(
        self,
        spec: ExperimentSpec,
    ) -> None:
        try:
            response = await self._client.put(
                "/_rupturelab/fault",
                json=spec.fault.model_dump(mode="json"),
            )
        except httpx2.RequestError as exc:
            raise ExperimentControlError("Could not reach the RuptureLab proxy") from exc

        if response.status_code >= 400:
            raise ExperimentControlError("Proxy rejected the experiment fault profile")

    async def _clear_fault(self) -> None:
        try:
            response = await self._client.delete("/_rupturelab/fault")
        except httpx2.RequestError as exc:
            raise ExperimentControlError("Could not reach the RuptureLab proxy") from exc

        if response.status_code != 204:
            raise ExperimentControlError("Proxy could not clear its fault profile")
