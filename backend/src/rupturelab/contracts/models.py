from typing import Literal

from pydantic import BaseModel, Field, model_validator

ContractPhase = Literal["baseline", "fault", "recovery"]
ContractMetric = Literal[
    "success_rate",
    "p95_latency_ms",
    "transport_errors",
    "fault_rate",
]
ContractOperator = Literal[">=", "<="]


class PhaseContract(BaseModel):
    min_success_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    max_p95_latency_ms: float | None = Field(
        default=None,
        ge=0.0,
    )
    max_transport_errors: int | None = Field(
        default=None,
        ge=0,
    )
    min_fault_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    @model_validator(mode="after")
    def require_at_least_one_check(self) -> "PhaseContract":
        checks = (
            self.min_success_rate,
            self.max_p95_latency_ms,
            self.max_transport_errors,
            self.min_fault_rate,
        )

        if all(check is None for check in checks):
            raise ValueError("A phase contract must configure at least one check")

        return self


class ResilienceContract(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    baseline: PhaseContract | None = None
    fault: PhaseContract | None = None
    recovery: PhaseContract | None = None

    @model_validator(mode="after")
    def require_at_least_one_phase(self) -> "ResilienceContract":
        if self.baseline is None and self.fault is None and self.recovery is None:
            raise ValueError("A resilience contract must configure at least one phase")

        return self


class ContractCheck(BaseModel):
    phase: ContractPhase
    metric: ContractMetric
    operator: ContractOperator
    expected: float | int
    observed: float | int
    passed: bool


class ContractEvaluation(BaseModel):
    contract_name: str
    passed: bool
    checks: list[ContractCheck]
