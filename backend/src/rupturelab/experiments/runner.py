import asyncio
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

import httpx2

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
    ) -> ExperimentResult:
        started_at = datetime.now(timezone.utc)

        await self._clear_fault()

        baseline = await self._run_phase(
            "baseline",
            spec,
        )

        await self._configure_fault(spec)

        try:
            fault = await self._run_phase(
                "fault",
                spec,
            )
        finally:
            await self._clear_fault()

        recovery = await self._run_phase(
            "recovery",
            spec,
        )

        return ExperimentResult(
            experiment_id=str(uuid4()),
            name=spec.name,
            started_at=started_at.isoformat(),
            spec=spec,
            phases=[
                baseline,
                fault,
                recovery,
            ],
        )

    async def _run_phase(
        self,
        phase: PhaseName,
        spec: ExperimentSpec,
    ) -> PhaseResult:
        measurements: list[RequestMeasurement] = []

        for index in range(spec.requests_per_phase):
            measurements.append(await self._send_request(spec))

            if spec.interval_ms > 0 and index < spec.requests_per_phase - 1:
                await asyncio.sleep(spec.interval_ms / 1000)

        return summarize_phase(
            phase,
            measurements,
        )

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
