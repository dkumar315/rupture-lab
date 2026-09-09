import httpx2
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse, Response

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

    body = await request.body()

    try:
        upstream = await client.request(
            method=request.method,
            url=request.url.path,
            params=request.query_params.multi_items(),
            headers=build_upstream_headers(request.headers),
            content=body,
        )
    except httpx2.RequestError:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": "Upstream service unavailable"},
        )

    response = Response(
        content=upstream.content,
        status_code=upstream.status_code,
    )

    response.raw_headers.extend(build_downstream_headers(upstream.headers))

    return response
