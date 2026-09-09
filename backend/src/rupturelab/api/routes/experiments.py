from fastapi import APIRouter, HTTPException, Request, status

from rupturelab.experiments.models import (
    ExperimentResult,
    ExperimentSpec,
)
from rupturelab.experiments.runner import (
    ExperimentControlError,
    ExperimentRunner,
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
    runner = ExperimentRunner(request.app.state.proxy_client)

    try:
        return await runner.run(spec)
    except ExperimentControlError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
