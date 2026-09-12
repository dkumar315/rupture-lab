import asyncio
from uuid import uuid4

import pytest

from rupturelab.experiments.events import ExperimentEvent, ExperimentEventBroker


def test_event_broker_replays_sequences_and_reports_terminal_streams() -> None:
    async def exercise() -> None:
        broker = ExperimentEventBroker(max_streams=2, max_events_per_stream=4)
        experiment_id = uuid4()
        publisher = broker.create(experiment_id)

        first = await broker.publish(
            experiment_id,
            ExperimentEvent(
                experiment_id=str(experiment_id),
                type="experiment.started",
                name="streamed",
            ),
        )
        await publisher.experiment_failed("boom")

        assert first.sequence == 1
        assert broker.contains(experiment_id) is True

        first_read = await broker.read(
            experiment_id,
            after_sequence=0,
            timeout_seconds=0.01,
        )
        assert first_read.event is not None
        assert first_read.event.sequence == 1
        assert first_read.terminal is False

        terminal_read = await broker.read(
            experiment_id,
            after_sequence=1,
            timeout_seconds=0.01,
        )
        assert terminal_read.event is not None
        assert terminal_read.event.sequence == 2
        assert terminal_read.terminal is True

        exhausted = await broker.read(
            experiment_id,
            after_sequence=2,
            timeout_seconds=0.01,
        )
        assert exhausted.event is None
        assert exhausted.terminal is True

    asyncio.run(exercise())


def test_event_broker_times_out_waiting_for_new_events() -> None:
    async def exercise() -> None:
        broker = ExperimentEventBroker()
        experiment_id = uuid4()
        broker.create(experiment_id)

        read = await broker.read(
            experiment_id,
            after_sequence=0,
            timeout_seconds=0.001,
        )

        assert read.event is None
        assert read.terminal is False

    asyncio.run(exercise())


def test_event_broker_evicts_completed_stream_and_guards_capacity() -> None:
    async def exercise() -> None:
        broker = ExperimentEventBroker(max_streams=1, max_events_per_stream=2)
        completed_id = uuid4()
        completed = broker.create(completed_id)
        await completed.experiment_failed("finished")

        replacement_id = uuid4()
        broker.create(replacement_id)
        assert broker.contains(completed_id) is False
        assert broker.contains(replacement_id) is True

        with pytest.raises(RuntimeError, match="capacity is exhausted"):
            broker.create(uuid4())

    asyncio.run(exercise())


def test_event_broker_rejects_invalid_limits_duplicates_and_unknown_streams() -> None:
    with pytest.raises(ValueError, match="limits must be positive"):
        ExperimentEventBroker(max_streams=0)

    with pytest.raises(ValueError, match="limits must be positive"):
        ExperimentEventBroker(max_events_per_stream=0)

    async def exercise() -> None:
        broker = ExperimentEventBroker()
        experiment_id = uuid4()
        broker.create(experiment_id)

        with pytest.raises(ValueError, match="already exists"):
            broker.create(experiment_id)

        unknown_id = uuid4()
        with pytest.raises(KeyError):
            await broker.publish(
                unknown_id,
                ExperimentEvent(
                    experiment_id=str(unknown_id),
                    type="experiment.started",
                ),
            )

        with pytest.raises(KeyError):
            await broker.read(
                unknown_id,
                after_sequence=0,
                timeout_seconds=0.01,
            )

    asyncio.run(exercise())
