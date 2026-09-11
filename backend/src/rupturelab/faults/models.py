from typing import Literal

from pydantic import BaseModel, Field, model_validator

HttpMethod = Literal[
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
    "HEAD",
]


def default_http_methods() -> list[HttpMethod]:
    return [
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
        "HEAD",
    ]


class FaultProfile(BaseModel):
    enabled: bool = False
    path_prefix: str = "/"
    methods: list[HttpMethod] = Field(default_factory=default_http_methods)
    probability: float = Field(default=1.0, ge=0.0, le=1.0)

    latency_ms: int = Field(default=0, ge=0, le=30_000)
    error_status: int | None = Field(default=None, ge=400, le=599)
    timeout_ms: int | None = Field(default=None, ge=1, le=30_000)
    malformed_json: bool = False

    @model_validator(mode="after")
    def validate_profile(self) -> FaultProfile:
        if not self.path_prefix.startswith("/"):
            raise ValueError("path_prefix must start with '/'")

        terminal_faults = sum(
            [
                self.error_status is not None,
                self.timeout_ms is not None,
                self.malformed_json,
            ]
        )

        if terminal_faults > 1:
            raise ValueError(
                "Only one of error_status, timeout_ms or malformed_json can be configured at a time"
            )

        if self.enabled and self.latency_ms == 0 and terminal_faults == 0:
            raise ValueError("An enabled profile must configure at least one fault")

        return self
