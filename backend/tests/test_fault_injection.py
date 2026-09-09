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


def configure_fault(
    client: TestClient,
    **overrides: object,
) -> None:
    profile = {
        "enabled": True,
        "path_prefix": "/",
        "methods": ["GET", "POST"],
        "probability": 1.0,
        "latency_ms": 0,
        "error_status": None,
        "timeout_ms": None,
        "malformed_json": False,
    }

    profile.update(overrides)

    response = client.put(
        "/_rupturelab/fault",
        json=profile,
    )

    assert response.status_code == 200


def clear_fault(client: TestClient) -> None:
    response = client.delete("/_rupturelab/fault")

    assert response.status_code == 204


def test_http_failure_can_short_circuit_target(
    proxy_client: TestClient,
) -> None:
    configure_fault(
        proxy_client,
        path_prefix="/demo/orders",
        methods=["POST"],
        error_status=503,
    )

    response = proxy_client.post(
        "/demo/orders",
        json={
            "client_request_id": "fault-001",
            "product_id": "keyboard",
            "quantity": 1,
        },
    )

    assert response.status_code == 503
    assert response.headers["x-rupturelab-fault"] == "http-error"
    assert store.stats().total_orders == 0


def test_fault_is_scoped_by_path(
    proxy_client: TestClient,
) -> None:
    configure_fault(
        proxy_client,
        path_prefix="/demo/orders",
        methods=["POST"],
        error_status=503,
    )

    response = proxy_client.get("/demo/products")

    assert response.status_code == 200


def test_zero_probability_bypasses_fault(
    proxy_client: TestClient,
) -> None:
    configure_fault(
        proxy_client,
        probability=0.0,
        error_status=503,
    )

    response = proxy_client.get("/demo/products")

    assert response.status_code == 200


def test_latency_fault_marks_forwarded_response(
    proxy_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(
        "rupturelab.proxy.routes.asyncio.sleep",
        fake_sleep,
    )

    configure_fault(
        proxy_client,
        path_prefix="/demo/products",
        methods=["GET"],
        latency_ms=250,
    )

    response = proxy_client.get("/demo/products")

    assert response.status_code == 200
    assert response.headers["x-rupturelab-fault"] == "latency"
    assert response.headers["x-rupturelab-latency-ms"] == "250"
    assert sleeps == [0.25]


def test_timeout_can_hide_successful_write(
    proxy_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr(
        "rupturelab.proxy.routes.asyncio.sleep",
        fake_sleep,
    )

    payload = {
        "client_request_id": "timeout-001",
        "product_id": "keyboard",
        "quantity": 1,
    }

    configure_fault(
        proxy_client,
        path_prefix="/demo/orders",
        methods=["POST"],
        timeout_ms=500,
    )

    first = proxy_client.post(
        "/demo/orders",
        json=payload,
    )

    assert first.status_code == 504
    assert store.stats().total_orders == 1

    clear_fault(proxy_client)

    retry = proxy_client.post(
        "/demo/orders",
        json=payload,
    )

    assert retry.status_code == 201

    stats = store.stats()

    assert stats.total_orders == 2
    assert stats.duplicate_logical_writes == 1


def test_idempotency_prevents_duplicate_after_timeout(
    proxy_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr(
        "rupturelab.proxy.routes.asyncio.sleep",
        fake_sleep,
    )

    payload = {
        "client_request_id": "timeout-safe-001",
        "product_id": "mouse",
        "quantity": 1,
    }

    headers = {
        "Idempotency-Key": "timeout-safe-001",
    }

    configure_fault(
        proxy_client,
        path_prefix="/demo/orders",
        methods=["POST"],
        timeout_ms=500,
    )

    first = proxy_client.post(
        "/demo/orders",
        json=payload,
        headers=headers,
    )

    assert first.status_code == 504
    assert store.stats().total_orders == 1

    clear_fault(proxy_client)

    retry = proxy_client.post(
        "/demo/orders",
        json=payload,
        headers=headers,
    )

    assert retry.status_code == 200
    assert retry.json()["replayed"] is True

    stats = store.stats()

    assert stats.total_orders == 1
    assert stats.duplicate_logical_writes == 0


def test_malformed_json_replaces_upstream_body(
    proxy_client: TestClient,
) -> None:
    configure_fault(
        proxy_client,
        path_prefix="/demo/products",
        methods=["GET"],
        malformed_json=True,
    )

    response = proxy_client.get("/demo/products")

    assert response.status_code == 200
    assert response.headers["x-rupturelab-fault"] == "malformed-json"
    assert response.headers["content-type"].startswith("application/json")
    assert response.text == '{"rupturelab":"malformed"'


def test_invalid_terminal_fault_combination_is_rejected(
    proxy_client: TestClient,
) -> None:
    response = proxy_client.put(
        "/_rupturelab/fault",
        json={
            "enabled": True,
            "error_status": 503,
            "timeout_ms": 500,
        },
    )

    assert response.status_code == 422
