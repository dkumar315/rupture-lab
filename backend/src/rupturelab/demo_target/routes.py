from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from rupturelab.demo_target.models import (
    DemoStats,
    EchoResponse,
    Order,
    OrderCreate,
    OrderResult,
    Product,
)
from rupturelab.demo_target.store import store

router = APIRouter(prefix="/demo", tags=["demo-target"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/products", response_model=list[Product])
async def list_products() -> list[Product]:
    return store.list_products()


@router.get("/orders", response_model=list[Order])
async def list_orders() -> list[Order]:
    return store.list_orders()


@router.post(
    "/orders",
    response_model=OrderResult,
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
    request: OrderCreate,
    response: Response,
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key"),
    ] = None,
) -> OrderResult:
    try:
        order, replayed = store.create_order(request, idempotency_key)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown product: {request.product_id}",
        ) from exc

    if replayed:
        response.status_code = status.HTTP_200_OK

    return OrderResult(
        order=order,
        replayed=replayed,
    )


def build_echo_response(
    request: Request,
    response: Response,
    body: dict[str, str] | None,
) -> EchoResponse:
    response.headers["X-Demo-Target"] = "rupturelab"

    return EchoResponse(
        method=request.method,
        query=list(request.query_params.multi_items()),
        trace_id=request.headers.get("x-trace-id"),
        body=body,
    )


@router.get("/echo", response_model=EchoResponse)
async def echo_get(
    request: Request,
    response: Response,
) -> EchoResponse:
    return build_echo_response(request, response, None)


@router.post("/echo", response_model=EchoResponse)
async def echo_post(
    request: Request,
    response: Response,
) -> EchoResponse:
    body: dict[str, str] = await request.json()

    return build_echo_response(request, response, body)


@router.get("/stats", response_model=DemoStats)
async def stats() -> DemoStats:
    return store.stats()


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset() -> Response:
    store.reset()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
