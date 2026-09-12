from typing import cast

from fastapi import APIRouter, Request, Response, status

from rupturelab.experiments.service import ExperimentService

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def readiness(
    request: Request,
    response: Response,
) -> dict[str, str]:
    service = cast(
        ExperimentService,
        request.app.state.experiment_service,
    )
    dependencies = await service.readiness()
    ready = all(dependencies.values())

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if ready else "not_ready",
        "database": "ok" if dependencies["database"] else "unavailable",
        "proxy": "ok" if dependencies["proxy"] else "unavailable",
    }
