from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from rupturelab.contracts.models import (
    ContractEvaluation,
    ResilienceContract,
)
from rupturelab.faults.models import FaultProfile, HttpMethod
from rupturelab.request_targets import local_request_path

PhaseName = Literal["baseline", "fault", "recovery"]


class ExperimentSpec(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    method: HttpMethod = "GET"
    path: str = Field(min_length=1, max_length=2048)
    requests_per_phase: int = Field(default=5, ge=1, le=100)
    interval_ms: int = Field(default=0, ge=0, le=5000)
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict[str, object] | None = None
    fault: FaultProfile
    contract: ResilienceContract | None = None

    @model_validator(mode="after")
    def validate_spec(self) -> ExperimentSpec:
        target_path = local_request_path(self.path)

        if not self.fault.enabled:
            raise ValueError("Experiment fault profile must be enabled")

        self.fault.path_prefix = target_path
        self.fault.methods = [self.method]

        return self


class RequestMeasurement(BaseModel):
    status_code: int | None
    duration_ms: float
    successful: bool
    fault: str | None = None
    error: str | None = None


class PhaseResult(BaseModel):
    phase: PhaseName
    request_count: int
    successful_requests: int
    failed_requests: int
    transport_errors: int
    faulted_requests: int
    status_codes: dict[str, int]
    average_latency_ms: float
    p95_latency_ms: float
    measurements: list[RequestMeasurement]


class ExperimentResult(BaseModel):
    experiment_id: str
    name: str
    started_at: str
    spec: ExperimentSpec
    phases: list[PhaseResult]
    contract_evaluation: ContractEvaluation | None = None


class ExperimentStart(BaseModel):
    experiment_id: str
    name: str


class ExperimentSummary(BaseModel):
    experiment_id: str
    name: str
    started_at: datetime
    completed_at: datetime
    method: HttpMethod
    path: str
    requests_per_phase: int
    interval_ms: int
    contract_passed: bool | None
