from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from rupturelab.db.base import Base


class ExperimentRunRecord(Base):
    __tablename__ = "experiment_runs"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    method: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    path: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )
    requests_per_phase: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    interval_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    spec: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
    )
    contract_passed: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )


class PhaseResultRecord(Base):
    __tablename__ = "phase_results"
    __table_args__ = (
        UniqueConstraint(
            "experiment_id",
            "phase",
            name="uq_phase_results_experiment_phase",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    experiment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "experiment_runs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    phase: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    request_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    successful_requests: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    failed_requests: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    transport_errors: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    faulted_requests: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    status_codes: Mapped[dict[str, int]] = mapped_column(
        JSON,
        nullable=False,
    )
    average_latency_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    p95_latency_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )


class RequestMeasurementRecord(Base):
    __tablename__ = "request_measurements"
    __table_args__ = (
        UniqueConstraint(
            "experiment_id",
            "phase",
            "sequence_number",
            name="uq_measurements_experiment_phase_sequence",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    experiment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "experiment_runs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    phase: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    status_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    duration_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    successful: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    fault: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


class ContractCheckRecord(Base):
    __tablename__ = "contract_checks"
    __table_args__ = (
        UniqueConstraint(
            "experiment_id",
            "sequence_number",
            name="uq_contract_checks_experiment_sequence",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    experiment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "experiment_runs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    phase: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    metric: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    operator: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )
    expected: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    observed: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    passed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
