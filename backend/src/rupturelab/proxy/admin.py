from typing import cast

from fastapi import APIRouter, Request, Response, status

from rupturelab.faults.engine import FaultEngine
from rupturelab.faults.models import FaultProfile

router = APIRouter(
    prefix="/_rupturelab",
    tags=["rupturelab"],
)


def get_fault_engine(request: Request) -> FaultEngine:
    return cast(
        FaultEngine,
        request.app.state.fault_engine,
    )


@router.get("/fault", response_model=FaultProfile)
async def get_fault_profile(
    request: Request,
) -> FaultProfile:
    return get_fault_engine(request).current()


@router.put("/fault", response_model=FaultProfile)
async def configure_fault_profile(
    profile: FaultProfile,
    request: Request,
) -> FaultProfile:
    return get_fault_engine(request).configure(profile)


@router.delete(
    "/fault",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def clear_fault_profile(
    request: Request,
) -> Response:
    get_fault_engine(request).reset()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
