import asyncio

import httpx2
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse, Response

from rupturelab.faults.engine import FaultEngine
from rupturelab.faults.models import FaultProfile
from rupturelab.proxy.headers import (
    build_downstream_headers,
    build_upstream_headers,
)

router = APIRouter()

SUPPORTED_METHODS = [
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
    "HEAD",
]


def build_fault_headers(
    fault_name: str,
    profile: FaultProfile,
) -> dict[str, str]:
    return {
        "X-RuptureLab-Fault": fault_name,
        "X-RuptureLab-Latency-Ms": str(profile.latency_ms),
    }


def build_upstream_response(
    upstream: httpx2.Response,
) -> Response:
    response = Response(
        content=upstream.content,
        status_code=upstream.status_code,
    )

    response.raw_headers.extend(build_downstream_headers(upstream.headers))

    return response


@router.api_route(
    "/",
    methods=SUPPORTED_METHODS,
    include_in_schema=False,
)
@router.api_route(
    "/{path:path}",
    methods=SUPPORTED_METHODS,
    include_in_schema=False,
)
async def forward_request(
    request: Request,
    path: str = "",
) -> Response:
    client: httpx2.AsyncClient = request.app.state.upstream_client
    engine: FaultEngine = request.app.state.fault_engine

    profile = engine.match(
        request.method,
        request.url.path,
    )

    if profile is not None and profile.latency_ms > 0:
        await asyncio.sleep(profile.latency_ms / 1000)

    if profile is not None and profile.error_status is not None:
        return JSONResponse(
            status_code=profile.error_status,
            content={
                "detail": "HTTP failure injected by RuptureLab",
            },
            headers=build_fault_headers(
                "http-error",
                profile,
            ),
        )

    body = await request.body()

    try:
        upstream = await client.request(
            method=request.method,
            url=request.url.path,
            params=request.url.query,
            headers=build_upstream_headers(request.headers),
            content=body,
        )
    except httpx2.RequestError:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "detail": "Upstream service unavailable",
            },
        )

    if profile is not None and profile.timeout_ms is not None:
        await asyncio.sleep(profile.timeout_ms / 1000)

        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={
                "detail": "Upstream response timed out after processing",
            },
            headers=build_fault_headers(
                "timeout",
                profile,
            ),
        )

    if profile is not None and profile.malformed_json:
        return Response(
            content=b'{"rupturelab":"malformed"',
            status_code=upstream.status_code,
            media_type="application/json",
            headers=build_fault_headers(
                "malformed-json",
                profile,
            ),
        )

    response = build_upstream_response(upstream)

    if profile is not None and profile.latency_ms > 0:
        response.headers["X-RuptureLab-Fault"] = "latency"
        response.headers["X-RuptureLab-Latency-Ms"] = str(profile.latency_ms)

    return response
