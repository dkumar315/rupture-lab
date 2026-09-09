import httpx2
from fastapi.testclient import TestClient

from rupturelab.main import create_app


class ScriptedProxyTransport(httpx2.AsyncBaseTransport):
    def __init__(self) -> None:
        self.fault_enabled = False
        self.control_calls: list[str] = []

    async def handle_async_request(
        self,
        request: httpx2.Request,
    ) -> httpx2.Response:
        path = request.url.path

        if path == "/_rupturelab/fault":
            if request.method == "PUT":
                self.fault_enabled = True
                self.control_calls.append("PUT")

                return httpx2.Response(
                    200,
                    json={"enabled": True},
                    request=request,
                )

            if request.method == "DELETE":
                self.fault_enabled = False
                self.control_calls.append("DELETE")

                return httpx2.Response(
                    204,
                    request=request,
                )

        if path == "/demo/products":
            if self.fault_enabled:
                return httpx2.Response(
                    503,
                    json={"detail": "HTTP failure injected by RuptureLab"},
                    headers={"X-RuptureLab-Fault": "http-error"},
                    request=request,
                )

            return httpx2.Response(
                200,
                json=[
                    {
                        "id": "keyboard",
                        "name": "Mechanical Keyboard",
                        "unit_price_cents": 12900,
                    }
                ],
                request=request,
            )

        if path == "/demo/unavailable":
            raise httpx2.ConnectError(
                "connection failed",
                request=request,
            )

        return httpx2.Response(
            404,
            request=request,
        )

    async def aclose(self) -> None:
        return None


def test_experiment_runs_baseline_fault_and_recovery() -> None:
    transport = ScriptedProxyTransport()

    app = create_app(
        proxy_url="http://proxy",
        transport=transport,
    )

    with TestClient(app) as client:
        response = client.post(
            "/experiments/run",
            json={
                "name": "products-503-recovery",
                "method": "GET",
                "path": "/demo/products",
                "requests_per_phase": 2,
                "fault": {
                    "enabled": True,
                    "path_prefix": "/demo/products",
                    "methods": ["GET"],
                    "probability": 1.0,
                    "error_status": 503,
                },
            },
        )

    assert response.status_code == 200

    result = response.json()
    phases = {phase["phase"]: phase for phase in result["phases"]}

    assert phases["baseline"]["successful_requests"] == 2
    assert phases["baseline"]["status_codes"] == {"200": 2}

    assert phases["fault"]["successful_requests"] == 0
    assert phases["fault"]["failed_requests"] == 2
    assert phases["fault"]["faulted_requests"] == 2
    assert phases["fault"]["status_codes"] == {"503": 2}

    assert phases["recovery"]["successful_requests"] == 2
    assert phases["recovery"]["status_codes"] == {"200": 2}

    assert transport.control_calls == [
        "DELETE",
        "PUT",
        "DELETE",
    ]


def test_experiment_records_transport_errors() -> None:
    transport = ScriptedProxyTransport()

    app = create_app(
        proxy_url="http://proxy",
        transport=transport,
    )

    with TestClient(app) as client:
        response = client.post(
            "/experiments/run",
            json={
                "name": "transport-errors",
                "method": "GET",
                "path": "/demo/unavailable",
                "requests_per_phase": 1,
                "fault": {
                    "enabled": True,
                    "path_prefix": "/demo/unavailable",
                    "methods": ["GET"],
                    "probability": 1.0,
                    "error_status": 503,
                },
            },
        )

    assert response.status_code == 200

    for phase in response.json()["phases"]:
        assert phase["request_count"] == 1
        assert phase["successful_requests"] == 0
        assert phase["failed_requests"] == 1
        assert phase["transport_errors"] == 1
        assert phase["measurements"][0]["status_code"] is None
        assert phase["measurements"][0]["error"] == "ConnectError"


def test_experiment_rejects_control_namespace() -> None:
    transport = ScriptedProxyTransport()

    app = create_app(
        proxy_url="http://proxy",
        transport=transport,
    )

    with TestClient(app) as client:
        response = client.post(
            "/experiments/run",
            json={
                "name": "invalid-target",
                "method": "GET",
                "path": "/_rupturelab/fault",
                "requests_per_phase": 1,
                "fault": {
                    "enabled": True,
                    "error_status": 503,
                },
            },
        )

    assert response.status_code == 422


def test_experiment_requires_enabled_fault() -> None:
    transport = ScriptedProxyTransport()

    app = create_app(
        proxy_url="http://proxy",
        transport=transport,
    )

    with TestClient(app) as client:
        response = client.post(
            "/experiments/run",
            json={
                "name": "disabled-fault",
                "method": "GET",
                "path": "/demo/products",
                "requests_per_phase": 1,
                "fault": {
                    "enabled": False,
                },
            },
        )

    assert response.status_code == 422
