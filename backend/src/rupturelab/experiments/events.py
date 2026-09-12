import asyncio
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from rupturelab.contracts.models import ContractEvaluation
from rupturelab.experiments.models import (
    ExperimentResult,
    ExperimentSpec,
    PhaseName,
    PhaseResult,
    RequestMeasurement,
)

ExperimentEventType = Literal[
    "experiment.started",
    "phase.started",
    "request.completed",
    "phase.completed",
    "contract.evaluated",
    "experiment.completed",
    "experiment.failed",
]

_TERMINAL_EVENT_TYPES = {"experiment.completed", "experiment.failed"}


class ExperimentEvent(BaseModel):
    sequence: int = Field(default=0, ge=0)
    experiment_id: str
    type: ExperimentEventType
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    name: str | None = None
    phase: PhaseName | None = None
    request_number: int | None = None
    requests_per_phase: int | None = None
    measurement: RequestMeasurement | None = None
    phase_result: PhaseResult | None = None
    contract_evaluation: ContractEvaluation | None = None
    result: ExperimentResult | None = None
    message: str | None = None


@dataclass(frozen=True)
class EventRead:
    event: ExperimentEvent | None
    terminal: bool


@dataclass
class _EventStream:
    max_events: int
    events: deque[ExperimentEvent] = field(init=False)
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)
    next_sequence: int = 1
    terminal: bool = False

    def __post_init__(self) -> None:
        self.events = deque(maxlen=self.max_events)


class ExperimentEventPublisher:
    def __init__(self, broker: ExperimentEventBroker, experiment_id: UUID) -> None:
        self._broker = broker
        self._experiment_id = experiment_id

    async def experiment_started(self, spec: ExperimentSpec) -> None:
        await self._broker.publish(
            self._experiment_id,
            ExperimentEvent(
                experiment_id=str(self._experiment_id),
                type="experiment.started",
                name=spec.name,
                requests_per_phase=spec.requests_per_phase,
            ),
        )

    async def phase_started(self, phase: PhaseName, requests_per_phase: int) -> None:
        await self._broker.publish(
            self._experiment_id,
            ExperimentEvent(
                experiment_id=str(self._experiment_id),
                type="phase.started",
                phase=phase,
                requests_per_phase=requests_per_phase,
            ),
        )

    async def request_completed(
        self,
        phase: PhaseName,
        request_number: int,
        requests_per_phase: int,
        measurement: RequestMeasurement,
    ) -> None:
        await self._broker.publish(
            self._experiment_id,
            ExperimentEvent(
                experiment_id=str(self._experiment_id),
                type="request.completed",
                phase=phase,
                request_number=request_number,
                requests_per_phase=requests_per_phase,
                measurement=measurement,
            ),
        )

    async def phase_completed(self, result: PhaseResult) -> None:
        await self._broker.publish(
            self._experiment_id,
            ExperimentEvent(
                experiment_id=str(self._experiment_id),
                type="phase.completed",
                phase=result.phase,
                phase_result=result,
            ),
        )

    async def contract_evaluated(self, evaluation: ContractEvaluation) -> None:
        await self._broker.publish(
            self._experiment_id,
            ExperimentEvent(
                experiment_id=str(self._experiment_id),
                type="contract.evaluated",
                contract_evaluation=evaluation,
            ),
        )

    async def experiment_completed(self, result: ExperimentResult) -> None:
        await self._broker.publish(
            self._experiment_id,
            ExperimentEvent(
                experiment_id=str(self._experiment_id),
                type="experiment.completed",
                result=result,
            ),
        )

    async def experiment_failed(self, message: str) -> None:
        await self._broker.publish(
            self._experiment_id,
            ExperimentEvent(
                experiment_id=str(self._experiment_id),
                type="experiment.failed",
                message=message,
            ),
        )


class ExperimentEventBroker:
    def __init__(
        self,
        *,
        max_streams: int = 32,
        max_events_per_stream: int = 512,
    ) -> None:
        if max_streams < 1 or max_events_per_stream < 1:
            raise ValueError("Event broker limits must be positive")

        self._max_streams = max_streams
        self._max_events_per_stream = max_events_per_stream
        self._streams: OrderedDict[UUID, _EventStream] = OrderedDict()

    def create(self, experiment_id: UUID) -> ExperimentEventPublisher:
        if experiment_id in self._streams:
            raise ValueError("Experiment event stream already exists")

        self._evict_if_full()
        self._streams[experiment_id] = _EventStream(self._max_events_per_stream)
        return ExperimentEventPublisher(self, experiment_id)

    def contains(self, experiment_id: UUID) -> bool:
        return experiment_id in self._streams

    async def publish(
        self,
        experiment_id: UUID,
        event: ExperimentEvent,
    ) -> ExperimentEvent:
        stream = self._streams.get(experiment_id)
        if stream is None:
            raise KeyError(experiment_id)

        async with stream.condition:
            sequenced = event.model_copy(update={"sequence": stream.next_sequence})
            stream.next_sequence += 1
            stream.events.append(sequenced)

            if sequenced.type in _TERMINAL_EVENT_TYPES:
                stream.terminal = True

            stream.condition.notify_all()
            return sequenced

    async def read(
        self,
        experiment_id: UUID,
        *,
        after_sequence: int,
        timeout_seconds: float,
    ) -> EventRead:
        stream = self._streams.get(experiment_id)
        if stream is None:
            raise KeyError(experiment_id)

        async with stream.condition:
            while True:
                event = next(
                    (item for item in stream.events if item.sequence > after_sequence),
                    None,
                )
                if event is not None:
                    return EventRead(
                        event=event,
                        terminal=event.type in _TERMINAL_EVENT_TYPES,
                    )

                if stream.terminal:
                    return EventRead(event=None, terminal=True)

                try:
                    await asyncio.wait_for(
                        stream.condition.wait(),
                        timeout=timeout_seconds,
                    )
                except TimeoutError:
                    return EventRead(event=None, terminal=False)

    def _evict_if_full(self) -> None:
        if len(self._streams) < self._max_streams:
            return

        completed_id = next(
            (experiment_id for experiment_id, stream in self._streams.items() if stream.terminal),
            None,
        )
        if completed_id is None:
            raise RuntimeError("Event broker capacity is exhausted")

        del self._streams[completed_id]
