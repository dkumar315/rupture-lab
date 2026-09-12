from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rupturelab.contracts.models import (
    ContractCheck,
    ContractEvaluation,
    ContractMetric,
    ContractOperator,
    ContractPhase,
)
from rupturelab.db.models import (
    ContractCheckRecord,
    ExperimentRunRecord,
    PhaseResultRecord,
    RequestMeasurementRecord,
)
from rupturelab.experiments.models import (
    ExperimentResult,
    ExperimentSpec,
    ExperimentSummary,
    PhaseName,
    PhaseResult,
    RequestMeasurement,
)
from rupturelab.faults.models import HttpMethod


class ExperimentRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def ready(self) -> bool:
        try:
            async with self._session_factory() as session:
                await session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return False

        return True

    async def save(
        self,
        result: ExperimentResult,
    ) -> None:
        experiment_id = UUID(result.experiment_id)

        contract_passed = (
            result.contract_evaluation.passed if result.contract_evaluation is not None else None
        )

        run_record = ExperimentRunRecord(
            id=experiment_id,
            name=result.name,
            started_at=datetime.fromisoformat(result.started_at),
            completed_at=datetime.now(UTC),
            method=result.spec.method,
            path=result.spec.path,
            requests_per_phase=result.spec.requests_per_phase,
            interval_ms=result.spec.interval_ms,
            spec=cast(
                dict[str, object],
                result.spec.model_dump(mode="json"),
            ),
            contract_passed=contract_passed,
        )

        phase_records: list[PhaseResultRecord] = []
        measurement_records: list[RequestMeasurementRecord] = []

        for phase in result.phases:
            phase_records.append(
                PhaseResultRecord(
                    experiment_id=experiment_id,
                    phase=phase.phase,
                    request_count=phase.request_count,
                    successful_requests=phase.successful_requests,
                    failed_requests=phase.failed_requests,
                    transport_errors=phase.transport_errors,
                    faulted_requests=phase.faulted_requests,
                    status_codes=phase.status_codes,
                    average_latency_ms=phase.average_latency_ms,
                    p95_latency_ms=phase.p95_latency_ms,
                )
            )

            for sequence_number, measurement in enumerate(
                phase.measurements,
                start=1,
            ):
                measurement_records.append(
                    RequestMeasurementRecord(
                        experiment_id=experiment_id,
                        phase=phase.phase,
                        sequence_number=sequence_number,
                        status_code=measurement.status_code,
                        duration_ms=measurement.duration_ms,
                        successful=measurement.successful,
                        fault=measurement.fault,
                        error=measurement.error,
                    )
                )

        contract_records: list[ContractCheckRecord] = []

        if result.contract_evaluation is not None:
            for sequence_number, check in enumerate(
                result.contract_evaluation.checks,
                start=1,
            ):
                contract_records.append(
                    ContractCheckRecord(
                        experiment_id=experiment_id,
                        sequence_number=sequence_number,
                        phase=check.phase,
                        metric=check.metric,
                        operator=check.operator,
                        expected=float(check.expected),
                        observed=float(check.observed),
                        passed=check.passed,
                    )
                )

        async with self._session_factory() as session:
            async with session.begin():
                session.add(run_record)
                await session.flush()
                session.add_all(phase_records)
                session.add_all(measurement_records)
                session.add_all(contract_records)

    async def list_summaries(
        self,
        *,
        limit: int,
        offset: int,
    ) -> list[ExperimentSummary]:
        statement = (
            select(ExperimentRunRecord)
            .order_by(
                ExperimentRunRecord.started_at.desc(),
                ExperimentRunRecord.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        async with self._session_factory() as session:
            runs = (await session.scalars(statement)).all()

        return [
            ExperimentSummary(
                experiment_id=str(run.id),
                name=run.name,
                started_at=run.started_at,
                completed_at=run.completed_at,
                method=cast(HttpMethod, run.method),
                path=run.path,
                requests_per_phase=run.requests_per_phase,
                interval_ms=run.interval_ms,
                contract_passed=run.contract_passed,
            )
            for run in runs
        ]

    async def get(
        self,
        experiment_id: UUID,
    ) -> ExperimentResult | None:
        async with self._session_factory() as session:
            run = await session.get(
                ExperimentRunRecord,
                experiment_id,
            )

            if run is None:
                return None

            phase_records = (
                await session.scalars(
                    select(PhaseResultRecord)
                    .where(PhaseResultRecord.experiment_id == experiment_id)
                    .order_by(PhaseResultRecord.id)
                )
            ).all()
            measurement_records = (
                await session.scalars(
                    select(RequestMeasurementRecord)
                    .where(RequestMeasurementRecord.experiment_id == experiment_id)
                    .order_by(RequestMeasurementRecord.id)
                )
            ).all()
            contract_records = (
                await session.scalars(
                    select(ContractCheckRecord)
                    .where(ContractCheckRecord.experiment_id == experiment_id)
                    .order_by(ContractCheckRecord.sequence_number)
                )
            ).all()

        measurements_by_phase: dict[str, list[RequestMeasurement]] = {}

        for measurement in measurement_records:
            measurements_by_phase.setdefault(measurement.phase, []).append(
                RequestMeasurement(
                    status_code=measurement.status_code,
                    duration_ms=measurement.duration_ms,
                    successful=measurement.successful,
                    fault=measurement.fault,
                    error=measurement.error,
                )
            )

        phases = [
            PhaseResult(
                phase=cast(PhaseName, phase.phase),
                request_count=phase.request_count,
                successful_requests=phase.successful_requests,
                failed_requests=phase.failed_requests,
                transport_errors=phase.transport_errors,
                faulted_requests=phase.faulted_requests,
                status_codes=phase.status_codes,
                average_latency_ms=phase.average_latency_ms,
                p95_latency_ms=phase.p95_latency_ms,
                measurements=measurements_by_phase.get(phase.phase, []),
            )
            for phase in phase_records
        ]

        spec = ExperimentSpec.model_validate(run.spec)
        contract_evaluation: ContractEvaluation | None = None

        if spec.contract is not None:
            checks = [
                ContractCheck(
                    phase=cast(ContractPhase, record.phase),
                    metric=cast(ContractMetric, record.metric),
                    operator=cast(ContractOperator, record.operator),
                    expected=record.expected,
                    observed=record.observed,
                    passed=record.passed,
                )
                for record in contract_records
            ]

            contract_evaluation = ContractEvaluation(
                contract_name=spec.contract.name,
                passed=run.contract_passed is True,
                checks=checks,
            )

        return ExperimentResult(
            experiment_id=str(run.id),
            name=run.name,
            started_at=run.started_at.isoformat(),
            spec=spec,
            phases=phases,
            contract_evaluation=contract_evaluation,
        )
