import asyncio
import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from rupturelab.contracts.models import (
    ContractCheck,
    ContractEvaluation,
    PhaseContract,
    ResilienceContract,
)
from rupturelab.db.models import ExperimentRunRecord
from rupturelab.db.repository import ExperimentRepository
from rupturelab.db.session import (
    create_database_engine,
    create_session_factory,
)
from rupturelab.experiments.models import (
    ExperimentResult,
    ExperimentSpec,
    PhaseName,
    PhaseResult,
    RequestMeasurement,
)
from rupturelab.faults.models import FaultProfile


def persisted_result() -> ExperimentResult:
    spec = ExperimentSpec(
        name="postgres-restart-proof",
        path="/demo/products",
        requests_per_phase=1,
        fault=FaultProfile(
            enabled=True,
            path_prefix="/demo/products",
            methods=["GET"],
            error_status=503,
        ),
        contract=ResilienceContract(
            name="postgres-recovery-contract",
            recovery=PhaseContract(min_success_rate=1.0),
        ),
    )

    phase_names: tuple[PhaseName, ...] = ("baseline", "fault", "recovery")

    phases = [
        PhaseResult(
            phase=phase,
            request_count=1,
            successful_requests=1,
            failed_requests=0,
            transport_errors=0,
            faulted_requests=0,
            status_codes={"200": 1},
            average_latency_ms=1.0,
            p95_latency_ms=1.0,
            measurements=[
                RequestMeasurement(
                    status_code=200,
                    duration_ms=1.0,
                    successful=True,
                )
            ],
        )
        for phase in phase_names
    ]

    return ExperimentResult(
        experiment_id=str(uuid4()),
        name=spec.name,
        started_at=datetime.now(UTC).isoformat(),
        spec=spec,
        phases=phases,
        contract_evaluation=ContractEvaluation(
            contract_name="postgres-recovery-contract",
            passed=True,
            checks=[
                ContractCheck(
                    phase="recovery",
                    metric="success_rate",
                    operator=">=",
                    expected=1.0,
                    observed=1.0,
                    passed=True,
                )
            ],
        ),
    )


def test_postgres_persists_across_engine_restart() -> None:
    database_url = os.environ.get("RUPTURELAB_DATABASE_URL")

    if database_url is None:
        pytest.skip("RUPTURELAB_DATABASE_URL is not configured")

    assert database_url is not None

    async def exercise() -> None:
        result = persisted_result()
        experiment_id = UUID(result.experiment_id)

        first_engine = create_database_engine(database_url)
        first_repository = ExperimentRepository(create_session_factory(first_engine))
        await first_repository.save(result)
        await first_engine.dispose()

        second_engine = create_database_engine(database_url)
        second_session_factory = create_session_factory(second_engine)
        second_repository = ExperimentRepository(second_session_factory)
        loaded = await second_repository.get(experiment_id)

        assert loaded is not None
        assert loaded.experiment_id == result.experiment_id
        assert loaded.name == result.name
        assert loaded.phases == result.phases
        assert loaded.contract_evaluation == result.contract_evaluation

        async with second_session_factory() as session:
            async with session.begin():
                record = await session.get(ExperimentRunRecord, experiment_id)
                assert record is not None
                await session.delete(record)

        await second_engine.dispose()

    asyncio.run(exercise())
