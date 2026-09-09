import httpx2
from starlette.datastructures import Headers


HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}

REQUEST_EXCLUDED_HEADERS = HOP_BY_HOP_HEADERS | {
    "accept-encoding",
    "content-length",
    "host",
}

RESPONSE_EXCLUDED_HEADERS = HOP_BY_HOP_HEADERS | {
    "content-encoding",
    "content-length",
}


def build_upstream_headers(headers: Headers) -> list[tuple[str, str]]:
    forwarded = [
        (
            name.decode("latin-1"),
            value.decode("latin-1"),
        )
        for name, value in headers.raw
        if name.decode("latin-1").lower() not in REQUEST_EXCLUDED_HEADERS
    ]

    forwarded.append(("accept-encoding", "identity"))

    return forwarded


def build_downstream_headers(
    headers: httpx2.Headers,
) -> list[tuple[bytes, bytes]]:
    return [
        (
            name.encode("latin-1"),
            value.encode("latin-1"),
        )
        for name, value in headers.multi_items()
        if name.lower() not in RESPONSE_EXCLUDED_HEADERS
    ]
