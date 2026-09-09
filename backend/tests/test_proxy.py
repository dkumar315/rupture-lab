from collections.abc import Iterator

import httpx2
import pytest
from fastapi.testclient import TestClient

from rupturelab.demo_target.main import app as demo_app
from rupturelab.demo_target.store import store
from rupturelab.proxy.main import create_proxy_app


@pytest.fixture(autouse=True)
def reset_demo_store() -> None:
    store.reset()
    yield
    store.reset()


@pytest.fixture
def proxy_client() -> Iterator[TestClient]:
    transport = httpx2.ASGITransport(app=demo_app)
    app = create_proxy_app(
        target_url="http://demo-target",
        transport=transport,
    )

    with TestClient(app) as client:
        yield client


def test_get_request_is_forwarded(proxy_client: TestClient) -> None:
    response = proxy_client.get("/demo/products")

    assert response.status_code == 200
    assert [product["id"] for product in response.json()] == [
        "keyboard",
        "mouse",
    ]


def test_query_headers_body_and_response_headers_are_forwarded(
    proxy_client: TestClient,
) -> None:
    response = proxy_client.post(
        "/demo/echo?tag=one&tag=two",
        headers={"X-Trace-ID": "proxy-trace-001"},
        json={"message": "through-proxy"},
    )

    assert response.status_code == 200
    assert response.headers["x-demo-target"] == "rupturelab"
    assert response.json() == {
        "method": "POST",
        "query": [["tag", "one"], ["tag", "two"]],
        "trace_id": "proxy-trace-001",
        "body": {"message": "through-proxy"},
    }


def test_idempotency_header_survives_proxy(
    proxy_client: TestClient,
) -> None:
    payload = {
        "client_request_id": "proxy-checkout-001",
        "product_id": "keyboard",
        "quantity": 1,
    }
    headers = {
        "Idempotency-Key": "proxy-checkout-001",
    }

    first = proxy_client.post(
        "/demo/orders",
        headers=headers,
        json=payload,
    )
    second = proxy_client.post(
        "/demo/orders",
        headers=headers,
        json=payload,
    )

    assert first.status_code == 201
    assert second.status_code == 200

    assert first.json()["order"]["id"] == second.json()["order"]["id"]
    assert second.json()["replayed"] is True


def test_upstream_status_code_and_body_are_preserved(
    proxy_client: TestClient,
) -> None:
    response = proxy_client.post(
        "/demo/orders",
        json={
            "client_request_id": "proxy-checkout-002",
            "product_id": "missing-product",
            "quantity": 1,
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Unknown product: missing-product",
    }


class FailingTransport(httpx2.AsyncBaseTransport):
    async def handle_async_request(
        self,
        request: httpx2.Request,
    ) -> httpx2.Response:
        raise httpx2.ConnectError(
            "upstream unavailable",
            request=request,
        )

    async def aclose(self) -> None:
        return None


def test_unreachable_upstream_returns_bad_gateway() -> None:
    app = create_proxy_app(
        target_url="http://unavailable",
        transport=FailingTransport(),
    )

    with TestClient(app) as client:
        response = client.get("/demo/products")

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Upstream service unavailable",
    }
