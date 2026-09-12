from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from rupturelab.demo_target.main import app
from rupturelab.demo_target.store import store

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_store() -> Iterator[None]:
    store.reset()
    yield
    store.reset()


def test_products_are_available() -> None:
    response = client.get("/demo/products")

    assert response.status_code == 200
    assert [product["id"] for product in response.json()] == [
        "keyboard",
        "mouse",
    ]


def test_repeated_logical_write_without_idempotency_creates_duplicate() -> None:
    payload = {
        "client_request_id": "checkout-001",
        "product_id": "keyboard",
        "quantity": 1,
    }

    first = client.post("/demo/orders", json=payload)
    second = client.post("/demo/orders", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["order"]["id"] == "ord-0001"
    assert second.json()["order"]["id"] == "ord-0002"

    stats = client.get("/demo/stats").json()

    assert stats == {
        "total_orders": 2,
        "unique_client_requests": 1,
        "duplicate_logical_writes": 1,
    }


def test_idempotency_key_replays_original_order() -> None:
    payload = {
        "client_request_id": "checkout-002",
        "product_id": "mouse",
        "quantity": 2,
    }
    headers = {"Idempotency-Key": "checkout-002"}

    first = client.post("/demo/orders", json=payload, headers=headers)
    second = client.post("/demo/orders", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 200

    assert first.json()["replayed"] is False
    assert second.json()["replayed"] is True

    assert first.json()["order"]["id"] == second.json()["order"]["id"]

    stats = client.get("/demo/stats").json()

    assert stats["total_orders"] == 1
    assert stats["duplicate_logical_writes"] == 0


def test_unknown_product_is_rejected() -> None:
    response = client.post(
        "/demo/orders",
        json={
            "client_request_id": "checkout-003",
            "product_id": "missing-product",
            "quantity": 1,
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Unknown product: missing-product",
    }


def test_reset_clears_orders() -> None:
    client.post(
        "/demo/orders",
        json={
            "client_request_id": "checkout-004",
            "product_id": "keyboard",
            "quantity": 1,
        },
    )

    response = client.post("/demo/reset")

    assert response.status_code == 204

    stats = client.get("/demo/stats").json()

    assert stats["total_orders"] == 0
    assert stats["duplicate_logical_writes"] == 0


def test_echo_reports_request_details() -> None:
    response = client.post(
        "/demo/echo?tag=one&tag=two",
        headers={"X-Trace-ID": "trace-123"},
        json={"message": "hello"},
    )

    assert response.status_code == 200
    assert response.headers["x-demo-target"] == "rupturelab"
    assert response.json() == {
        "method": "POST",
        "query": [["tag", "one"], ["tag", "two"]],
        "trace_id": "trace-123",
        "body": {"message": "hello"},
    }


def test_echo_operations_have_unique_openapi_ids() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200

    echo_path = response.json()["paths"]["/demo/echo"]

    assert echo_path["get"]["operationId"] != echo_path["post"]["operationId"]


def test_orders_endpoint_lists_created_orders() -> None:
    client.post(
        "/demo/orders",
        json={
            "client_request_id": "list-orders-001",
            "product_id": "keyboard",
            "quantity": 1,
        },
    )

    response = client.get("/demo/orders")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == "ord-0001"


def test_echo_get_reports_request_details() -> None:
    response = client.get(
        "/demo/echo?tag=one&tag=two",
        headers={"X-Trace-ID": "trace-get-001"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "method": "GET",
        "query": [["tag", "one"], ["tag", "two"]],
        "trace_id": "trace-get-001",
        "body": None,
    }


def test_demo_target_health_is_available() -> None:
    response = client.get("/demo/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
