import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select

from rupturelab.contracts.models import (
    ContractCheck,
    ContractEvaluation,
    PhaseContract,
    ResilienceContract,
)
from rupturelab.db.base import Base
from rupturelab.db.models import (
    ContractCheckRecord,
    ExperimentRunRecord,
    PhaseResultRecord,
    RequestMeasurementRecord,
)
from rupturelab.db.repository import ExperimentRepository
from rupturelab.db.session import (
    create_database_engine,
    create_session_factory,
)
from rupturelab.experiments.models import (
    ExperimentResult,
    ExperimentSpec,
    PhaseResult,
    RequestMeasurement,
)
from rupturelab.faults.models import FaultProfile


def experiment_result(
    *,
    with_contract: bool,
) -> ExperimentResult:
    experiment_id = str(uuid4())

    contract = (
        ResilienceContract(
            name="products-recovery",
            recovery=PhaseContract(
                min_success_rate=1.0,
            ),
        )
        if with_contract
        else None
    )

    spec = ExperimentSpec(
        name="persisted-experiment",
        method="GET",
        path="/demo/products",
        requests_per_phase=1,
        interval_ms=25,
        fault=FaultProfile(
            enabled=True,
            path_prefix="/demo/products",
            methods=["GET"],
            error_status=503,
        ),
        contract=contract,
    )

    phases = [
        PhaseResult(
            phase="baseline",
            request_count=1,
            successful_requests=1,
            failed_requests=0,
            transport_errors=0,
            faulted_requests=0,
            status_codes={"200": 1},
            average_latency_ms=12.5,
            p95_latency_ms=12.5,
            measurements=[
                RequestMeasurement(
                    status_code=200,
                    duration_ms=12.5,
                    successful=True,
                )
            ],
        ),
        PhaseResult(
            phase="fault",
            request_count=1,
            successful_requests=0,
            failed_requests=1,
            transport_errors=0,
            faulted_requests=1,
            status_codes={"503": 1},
            average_latency_ms=4.0,
            p95_latency_ms=4.0,
            measurements=[
                RequestMeasurement(
                    status_code=503,
                    duration_ms=4.0,
                    successful=False,
                    fault="http-error",
                )
            ],
        ),
        PhaseResult(
            phase="recovery",
            request_count=1,
            successful_requests=1,
            failed_requests=0,
            transport_errors=0,
            faulted_requests=0,
            status_codes={"200": 1},
            average_latency_ms=8.0,
            p95_latency_ms=8.0,
            measurements=[
                RequestMeasurement(
                    status_code=200,
                    duration_ms=8.0,
                    successful=True,
                )
            ],
        ),
    ]

    evaluation = (
        ContractEvaluation(
            contract_name="products-recovery",
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
        )
        if with_contract
        else None
    )

    return ExperimentResult(
        experiment_id=experiment_id,
        name=spec.name,
        started_at=datetime.now(UTC).isoformat(),
        spec=spec,
        phases=phases,
        contract_evaluation=evaluation,
    )


def test_repository_persists_complete_experiment() -> None:
    async def exercise() -> None:
        engine = create_database_engine("sqlite+aiosqlite:///:memory:")
        session_factory = create_session_factory(engine)

        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        result = experiment_result(with_contract=True)

        repository = ExperimentRepository(session_factory)
        await repository.save(result)

        async with session_factory() as session:
            run = await session.get(
                ExperimentRunRecord,
                UUID(result.experiment_id),
            )

            assert run is not None
            assert run.name == "persisted-experiment"
            assert run.method == "GET"
            assert run.path == "/demo/products"
            assert run.requests_per_phase == 1
            assert run.interval_ms == 25
            assert run.contract_passed is True
            assert run.spec["name"] == "persisted-experiment"
            assert run.completed_at is not None

            phase_count = await session.scalar(select(func.count()).select_from(PhaseResultRecord))
            measurement_count = await session.scalar(
                select(func.count()).select_from(RequestMeasurementRecord)
            )
            contract_count = await session.scalar(
                select(func.count()).select_from(ContractCheckRecord)
            )

            assert phase_count == 3
            assert measurement_count == 3
            assert contract_count == 1

            measurements = (
                await session.scalars(
                    select(RequestMeasurementRecord).order_by(RequestMeasurementRecord.id)
                )
            ).all()

            assert [measurement.status_code for measurement in measurements] == [200, 503, 200]

            assert measurements[1].fault == "http-error"

            contract_check = (await session.scalars(select(ContractCheckRecord))).one()

            assert contract_check.phase == "recovery"
            assert contract_check.metric == "success_rate"
            assert contract_check.operator == ">="
            assert contract_check.expected == 1.0
            assert contract_check.observed == 1.0
            assert contract_check.passed is True

        loaded = await repository.get(UUID(result.experiment_id))
        summaries = await repository.list_summaries(limit=50, offset=0)

        assert loaded is not None
        assert loaded.experiment_id == result.experiment_id
        assert loaded.name == result.name
        assert loaded.spec == result.spec
        assert loaded.phases == result.phases
        assert loaded.contract_evaluation == result.contract_evaluation
        loaded_started_at = datetime.fromisoformat(loaded.started_at).replace(tzinfo=UTC)
        expected_started_at = datetime.fromisoformat(result.started_at)

        assert loaded_started_at == expected_started_at

        assert len(summaries) == 1
        assert summaries[0].experiment_id == result.experiment_id
        assert summaries[0].name == result.name
        assert summaries[0].contract_passed is True

        await engine.dispose()

    asyncio.run(exercise())


def test_repository_persists_experiment_without_contract() -> None:
    async def exercise() -> None:
        engine = create_database_engine("sqlite+aiosqlite:///:memory:")
        session_factory = create_session_factory(engine)

        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        result = experiment_result(with_contract=False)

        repository = ExperimentRepository(session_factory)
        await repository.save(result)

        async with session_factory() as session:
            run = await session.get(
                ExperimentRunRecord,
                UUID(result.experiment_id),
            )

            assert run is not None
            assert run.contract_passed is None

            contract_count = await session.scalar(
                select(func.count()).select_from(ContractCheckRecord)
            )

            assert contract_count == 0

        loaded = await repository.get(UUID(result.experiment_id))
        missing = await repository.get(uuid4())

        assert loaded is not None
        assert loaded.contract_evaluation is None
        assert missing is None

        await engine.dispose()

    asyncio.run(exercise())


def test_repository_orders_and_paginates_history() -> None:
    async def exercise() -> None:
        engine = create_database_engine("sqlite+aiosqlite:///:memory:")
        session_factory = create_session_factory(engine)

        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        repository = ExperimentRepository(session_factory)
        older = experiment_result(with_contract=False).model_copy(
            update={
                "experiment_id": str(uuid4()),
                "name": "older",
                "started_at": "2026-09-11T05:00:00+00:00",
            }
        )
        newer = experiment_result(with_contract=False).model_copy(
            update={
                "experiment_id": str(uuid4()),
                "name": "newer",
                "started_at": "2026-09-11T06:00:00+00:00",
            }
        )

        await repository.save(older)
        await repository.save(newer)

        first_page = await repository.list_summaries(limit=1, offset=0)
        second_page = await repository.list_summaries(limit=1, offset=1)

        assert [summary.name for summary in first_page] == ["newer"]
        assert [summary.name for summary in second_page] == ["older"]

        await engine.dispose()

    asyncio.run(exercise())


def test_repository_reports_database_readiness() -> None:
    async def exercise() -> None:
        engine = create_database_engine("sqlite+aiosqlite:///:memory:")
        repository = ExperimentRepository(create_session_factory(engine))

        assert await repository.ready() is True

        await engine.dispose()

    asyncio.run(exercise())


def test_repository_reports_database_failure() -> None:
    from typing import cast

    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    class FailingSession:
        async def __aenter__(self) -> FailingSession:
            return self

        async def __aexit__(
            self,
            exc_type: object,
            exc_value: object,
            traceback: object,
        ) -> None:
            del exc_type, exc_value, traceback

        async def execute(self, statement: object) -> None:
            del statement
            raise SQLAlchemyError("database unavailable")

    class FailingSessionFactory:
        def __call__(self) -> FailingSession:
            return FailingSession()

    async def exercise() -> None:
        session_factory = cast(
            async_sessionmaker[AsyncSession],
            FailingSessionFactory(),
        )
        repository = ExperimentRepository(session_factory)

        assert await repository.ready() is False

    asyncio.run(exercise())
