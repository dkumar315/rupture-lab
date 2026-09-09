from rupturelab.contracts.models import (
    ContractCheck,
    ContractEvaluation,
    ContractMetric,
    ContractOperator,
    ContractPhase,
    PhaseContract,
    ResilienceContract,
)
from rupturelab.experiments.models import PhaseResult


def rate(count: int, total: int) -> float:
    if total == 0:
        return 0.0

    return count / total


def build_check(
    *,
    phase: ContractPhase,
    metric: ContractMetric,
    operator: ContractOperator,
    expected: float | int,
    observed: float | int,
) -> ContractCheck:
    if operator == ">=":
        passed = observed >= expected
    else:
        passed = observed <= expected

    return ContractCheck(
        phase=phase,
        metric=metric,
        operator=operator,
        expected=expected,
        observed=observed,
        passed=passed,
    )


def evaluate_contract(
    contract: ResilienceContract,
    phases: list[PhaseResult],
) -> ContractEvaluation:
    phase_map = {phase.phase: phase for phase in phases}

    configured_phases: tuple[
        tuple[ContractPhase, PhaseContract | None],
        ...,
    ] = (
        ("baseline", contract.baseline),
        ("fault", contract.fault),
        ("recovery", contract.recovery),
    )

    checks: list[ContractCheck] = []

    for phase_name, phase_contract in configured_phases:
        if phase_contract is None:
            continue

        phase = phase_map.get(phase_name)

        if phase is None:
            raise ValueError(f"Experiment result is missing phase '{phase_name}'")

        if phase_contract.min_success_rate is not None:
            checks.append(
                build_check(
                    phase=phase_name,
                    metric="success_rate",
                    operator=">=",
                    expected=phase_contract.min_success_rate,
                    observed=rate(
                        phase.successful_requests,
                        phase.request_count,
                    ),
                )
            )

        if phase_contract.max_p95_latency_ms is not None:
            checks.append(
                build_check(
                    phase=phase_name,
                    metric="p95_latency_ms",
                    operator="<=",
                    expected=phase_contract.max_p95_latency_ms,
                    observed=phase.p95_latency_ms,
                )
            )

        if phase_contract.max_transport_errors is not None:
            checks.append(
                build_check(
                    phase=phase_name,
                    metric="transport_errors",
                    operator="<=",
                    expected=phase_contract.max_transport_errors,
                    observed=phase.transport_errors,
                )
            )

        if phase_contract.min_fault_rate is not None:
            checks.append(
                build_check(
                    phase=phase_name,
                    metric="fault_rate",
                    operator=">=",
                    expected=phase_contract.min_fault_rate,
                    observed=rate(
                        phase.faulted_requests,
                        phase.request_count,
                    ),
                )
            )

    return ContractEvaluation(
        contract_name=contract.name,
        passed=all(check.passed for check in checks),
        checks=checks,
    )
