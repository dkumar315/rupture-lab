import pytest
from pydantic import ValidationError

from rupturelab.experiments.metrics import percentile, summarize_phase
from rupturelab.experiments.models import ExperimentSpec
from rupturelab.faults.engine import FaultEngine
from rupturelab.faults.models import FaultProfile


def test_percentile_of_empty_sample_is_zero() -> None:
    assert percentile([], 0.95) == 0.0


def test_empty_phase_summary_is_zeroed() -> None:
    result = summarize_phase("baseline", [])

    assert result.request_count == 0
    assert result.successful_requests == 0
    assert result.failed_requests == 0
    assert result.transport_errors == 0
    assert result.faulted_requests == 0
    assert result.status_codes == {}
    assert result.average_latency_ms == 0.0
    assert result.p95_latency_ms == 0.0


def test_experiment_path_requires_leading_slash() -> None:
    with pytest.raises(ValidationError):
        ExperimentSpec(
            name="invalid-path",
            path="demo/products",
            fault=FaultProfile(
                enabled=True,
                error_status=503,
            ),
        )


def test_fault_path_prefix_requires_leading_slash() -> None:
    with pytest.raises(ValidationError):
        FaultProfile(
            enabled=True,
            path_prefix="demo/products",
            error_status=503,
        )


def test_enabled_fault_requires_fault_behaviour() -> None:
    with pytest.raises(ValidationError):
        FaultProfile(enabled=True)


def test_fault_engine_current_returns_independent_copy() -> None:
    engine = FaultEngine()

    snapshot = engine.current()
    snapshot.enabled = True

    assert engine.current().enabled is False


def test_fault_engine_ignores_wrong_method() -> None:
    engine = FaultEngine()
    engine.configure(
        FaultProfile(
            enabled=True,
            path_prefix="/demo",
            methods=["GET"],
            error_status=503,
        )
    )

    assert engine.match("POST", "/demo/products") is None


def test_fault_engine_ignores_wrong_path() -> None:
    engine = FaultEngine()
    engine.configure(
        FaultProfile(
            enabled=True,
            path_prefix="/demo/orders",
            methods=["GET"],
            error_status=503,
        )
    )

    assert engine.match("GET", "/demo/products") is None
