import pytest
from pydantic import ValidationError

from rupturelab.contracts.evaluator import evaluate_contract
from rupturelab.contracts.models import (
    PhaseContract,
    ResilienceContract,
)
from rupturelab.experiments.models import PhaseName, PhaseResult


def phase_result(
    phase: PhaseName,
    *,
    request_count: int = 10,
    successful_requests: int = 10,
    transport_errors: int = 0,
    faulted_requests: int = 0,
    p95_latency_ms: float = 100.0,
) -> PhaseResult:
    return PhaseResult(
        phase=phase,
        request_count=request_count,
        successful_requests=successful_requests,
        failed_requests=request_count - successful_requests,
        transport_errors=transport_errors,
        faulted_requests=faulted_requests,
        status_codes={},
        average_latency_ms=p95_latency_ms,
        p95_latency_ms=p95_latency_ms,
        measurements=[],
    )


def test_phase_contract_requires_check() -> None:
    with pytest.raises(ValidationError):
        PhaseContract()


def test_resilience_contract_requires_phase() -> None:
    with pytest.raises(ValidationError):
        ResilienceContract(name="empty-contract")


def test_contract_passes_when_all_thresholds_are_met() -> None:
    contract = ResilienceContract(
        name="healthy-recovery",
        baseline=PhaseContract(
            min_success_rate=0.99,
            max_p95_latency_ms=200,
            max_transport_errors=0,
        ),
        fault=PhaseContract(
            min_fault_rate=1.0,
        ),
        recovery=PhaseContract(
            min_success_rate=1.0,
            max_p95_latency_ms=250,
            max_transport_errors=0,
        ),
    )

    evaluation = evaluate_contract(
        contract,
        [
            phase_result(
                "baseline",
                p95_latency_ms=120,
            ),
            phase_result(
                "fault",
                successful_requests=0,
                faulted_requests=10,
                p95_latency_ms=20,
            ),
            phase_result(
                "recovery",
                p95_latency_ms=140,
            ),
        ],
    )

    assert evaluation.passed is True
    assert len(evaluation.checks) == 7
    assert all(check.passed for check in evaluation.checks)


def test_contract_fails_when_threshold_is_missed() -> None:
    contract = ResilienceContract(
        name="failed-recovery",
        recovery=PhaseContract(
            min_success_rate=1.0,
            max_transport_errors=0,
        ),
    )

    evaluation = evaluate_contract(
        contract,
        [
            phase_result(
                "recovery",
                successful_requests=8,
                transport_errors=1,
            )
        ],
    )

    assert evaluation.passed is False
    assert len(evaluation.checks) == 2
    assert all(check.passed is False for check in evaluation.checks)


def test_contract_skips_unconfigured_phases() -> None:
    contract = ResilienceContract(
        name="baseline-only",
        baseline=PhaseContract(
            min_success_rate=1.0,
        ),
    )

    evaluation = evaluate_contract(
        contract,
        [
            phase_result("baseline"),
        ],
    )

    assert evaluation.passed is True
    assert len(evaluation.checks) == 1
    assert evaluation.checks[0].phase == "baseline"


def test_contract_rejects_missing_result_phase() -> None:
    contract = ResilienceContract(
        name="missing-recovery",
        recovery=PhaseContract(
            min_success_rate=1.0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="missing phase 'recovery'",
    ):
        evaluate_contract(
            contract,
            [
                phase_result("baseline"),
            ],
        )


def test_zero_request_phase_has_zero_rates() -> None:
    contract = ResilienceContract(
        name="empty-phase",
        baseline=PhaseContract(
            min_success_rate=0.0,
            min_fault_rate=0.0,
        ),
    )

    evaluation = evaluate_contract(
        contract,
        [
            phase_result(
                "baseline",
                request_count=0,
                successful_requests=0,
                faulted_requests=0,
            )
        ],
    )

    assert evaluation.passed is True

    observed = {check.metric: check.observed for check in evaluation.checks}

    assert observed["success_rate"] == 0.0
    assert observed["fault_rate"] == 0.0
