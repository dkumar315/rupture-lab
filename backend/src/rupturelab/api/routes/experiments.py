from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from rupturelab.experiments.models import (
    ExperimentResult,
    ExperimentSpec,
    ExperimentStart,
    ExperimentSummary,
)
from rupturelab.experiments.runner import ExperimentControlError
from rupturelab.experiments.service import (
    ExperimentBusyError,
    ExperimentService,
)

router = APIRouter(
    prefix="/experiments",
    tags=["experiments"],
)

_EVENT_HEARTBEAT_SECONDS = 15.0


@router.post(
    "/run",
    response_model=ExperimentResult,
)
async def run_experiment(
    spec: ExperimentSpec,
    request: Request,
) -> ExperimentResult:
    service: ExperimentService = request.app.state.experiment_service

    try:
        return await service.run(spec)
    except ExperimentBusyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ExperimentControlError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post(
    "/start",
    response_model=ExperimentStart,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_experiment(
    spec: ExperimentSpec,
    request: Request,
) -> ExperimentStart:
    service: ExperimentService = request.app.state.experiment_service

    try:
        return await service.start(spec)
    except ExperimentBusyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/{experiment_id}/events",
    response_class=StreamingResponse,
)
async def stream_experiment_events(
    experiment_id: UUID,
    request: Request,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    service: ExperimentService = request.app.state.experiment_service

    if not service.has_event_stream(experiment_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment event stream not found",
        )

    try:
        after_sequence = int(last_event_id) if last_event_id is not None else 0
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last-Event-ID must be an integer",
        ) from exc

    if after_sequence < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last-Event-ID must be non-negative",
        )

    async def events() -> AsyncIterator[str]:
        cursor = after_sequence

        while True:
            read = await service.read_event(
                experiment_id,
                after_sequence=cursor,
                timeout_seconds=_EVENT_HEARTBEAT_SECONDS,
            )

            if read.event is not None:
                cursor = read.event.sequence
                yield (f"id: {read.event.sequence}\ndata: {read.event.model_dump_json()}\n\n")

            if read.terminal:
                return

            if read.event is None:
                yield ": keepalive\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "",
    response_model=list[ExperimentSummary],
)
async def list_experiments(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ExperimentSummary]:
    service: ExperimentService = request.app.state.experiment_service

    return await service.list_summaries(
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{experiment_id}",
    response_model=ExperimentResult,
)
async def get_experiment(
    experiment_id: UUID,
    request: Request,
) -> ExperimentResult:
    service: ExperimentService = request.app.state.experiment_service
    result = await service.get(experiment_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found",
        )

    return result
