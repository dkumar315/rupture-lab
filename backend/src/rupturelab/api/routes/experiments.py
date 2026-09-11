from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from rupturelab.experiments.models import (
    ExperimentResult,
    ExperimentSpec,
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
