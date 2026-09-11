from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from rupturelab.experiments.models import ExperimentResult, ExperimentSummary
from rupturelab.main import create_app as build_app


class MemoryExperimentStore:
    def __init__(self) -> None:
        self.results: dict[UUID, ExperimentResult] = {}
        self.completed_at: dict[UUID, datetime] = {}

    async def save(self, result: ExperimentResult) -> None:
        experiment_id = UUID(result.experiment_id)
        self.results[experiment_id] = result
        self.completed_at[experiment_id] = datetime.now(UTC)

    async def list_summaries(
        self,
        *,
        limit: int,
        offset: int,
    ) -> list[ExperimentSummary]:
        ordered = sorted(
            self.results.items(),
            key=lambda item: item[1].started_at,
            reverse=True,
        )

        return [
            ExperimentSummary(
                experiment_id=str(experiment_id),
                name=result.name,
                started_at=datetime.fromisoformat(result.started_at),
                completed_at=self.completed_at[experiment_id],
                method=result.spec.method,
                path=result.spec.path,
                requests_per_phase=result.spec.requests_per_phase,
                interval_ms=result.spec.interval_ms,
                contract_passed=(
                    result.contract_evaluation.passed
                    if result.contract_evaluation is not None
                    else None
                ),
            )
            for experiment_id, result in ordered[offset : offset + limit]
        ]

    async def get(self, experiment_id: UUID) -> ExperimentResult | None:
        return self.results.get(experiment_id)


def create_test_app(
    *,
    proxy_url: str,
    transport: httpx2.AsyncBaseTransport,
) -> FastAPI:
    return build_app(
        proxy_url=proxy_url,
        transport=transport,
        experiment_store=MemoryExperimentStore(),
    )


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

    app = create_test_app(
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

    app = create_test_app(
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

    app = create_test_app(
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

    app = create_test_app(
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


class RejectFaultTransport(httpx2.AsyncBaseTransport):
    async def handle_async_request(
        self,
        request: httpx2.Request,
    ) -> httpx2.Response:
        if request.method == "DELETE":
            return httpx2.Response(204, request=request)

        if request.method == "PUT":
            return httpx2.Response(422, request=request)

        return httpx2.Response(200, request=request)

    async def aclose(self) -> None:
        return None


class ConfigureDisconnectTransport(httpx2.AsyncBaseTransport):
    async def handle_async_request(
        self,
        request: httpx2.Request,
    ) -> httpx2.Response:
        if request.method == "DELETE":
            return httpx2.Response(204, request=request)

        if request.method == "PUT":
            raise httpx2.ConnectError(
                "proxy disconnected",
                request=request,
            )

        return httpx2.Response(200, request=request)

    async def aclose(self) -> None:
        return None


class ClearDisconnectTransport(httpx2.AsyncBaseTransport):
    async def handle_async_request(
        self,
        request: httpx2.Request,
    ) -> httpx2.Response:
        raise httpx2.ConnectError(
            "proxy disconnected",
            request=request,
        )

    async def aclose(self) -> None:
        return None


class FailedRecoveryClearTransport(httpx2.AsyncBaseTransport):
    def __init__(self) -> None:
        self.delete_count = 0
        self.fault_enabled = False

    async def handle_async_request(
        self,
        request: httpx2.Request,
    ) -> httpx2.Response:
        if request.method == "DELETE":
            self.delete_count += 1

            if self.delete_count == 1:
                self.fault_enabled = False
                return httpx2.Response(204, request=request)

            return httpx2.Response(500, request=request)

        if request.method == "PUT":
            self.fault_enabled = True
            return httpx2.Response(
                200,
                json={"enabled": True},
                request=request,
            )

        if self.fault_enabled:
            return httpx2.Response(
                503,
                headers={"X-RuptureLab-Fault": "http-error"},
                request=request,
            )

        return httpx2.Response(200, request=request)

    async def aclose(self) -> None:
        return None


def experiment_payload(
    *,
    requests_per_phase: int = 1,
    interval_ms: int = 0,
) -> dict[str, object]:
    return {
        "name": "edge-case-experiment",
        "method": "GET",
        "path": "/demo/products",
        "requests_per_phase": requests_per_phase,
        "interval_ms": interval_ms,
        "fault": {
            "enabled": True,
            "path_prefix": "/demo/products",
            "methods": ["GET"],
            "probability": 1.0,
            "error_status": 503,
        },
    }


def test_experiment_reports_rejected_fault_configuration() -> None:
    app = create_test_app(
        proxy_url="http://proxy",
        transport=RejectFaultTransport(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/experiments/run",
            json=experiment_payload(),
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "Proxy rejected the experiment fault profile"}


def test_experiment_reports_fault_configuration_disconnect() -> None:
    app = create_test_app(
        proxy_url="http://proxy",
        transport=ConfigureDisconnectTransport(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/experiments/run",
            json=experiment_payload(),
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "Could not reach the RuptureLab proxy"}


def test_experiment_reports_initial_clear_disconnect() -> None:
    app = create_test_app(
        proxy_url="http://proxy",
        transport=ClearDisconnectTransport(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/experiments/run",
            json=experiment_payload(),
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "Could not reach the RuptureLab proxy"}


def test_experiment_reports_failed_fault_cleanup() -> None:
    app = create_test_app(
        proxy_url="http://proxy",
        transport=FailedRecoveryClearTransport(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/experiments/run",
            json=experiment_payload(),
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "Proxy could not clear its fault profile"}


def test_experiment_waits_between_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(
        "rupturelab.experiments.runner.asyncio.sleep",
        fake_sleep,
    )

    transport = ScriptedProxyTransport()

    app = create_test_app(
        proxy_url="http://proxy",
        transport=transport,
    )

    with TestClient(app) as client:
        response = client.post(
            "/experiments/run",
            json=experiment_payload(
                requests_per_phase=2,
                interval_ms=25,
            ),
        )

    assert response.status_code == 200
    assert sleeps == [0.025, 0.025, 0.025]


def test_experiment_evaluates_resilience_contract() -> None:
    transport = ScriptedProxyTransport()

    app = create_test_app(
        proxy_url="http://proxy",
        transport=transport,
    )

    payload = experiment_payload(
        requests_per_phase=2,
    )

    payload["contract"] = {
        "name": "products-recovery-contract",
        "baseline": {
            "min_success_rate": 1.0,
        },
        "fault": {
            "min_fault_rate": 1.0,
        },
        "recovery": {
            "min_success_rate": 1.0,
            "max_transport_errors": 0,
        },
    }

    with TestClient(app) as client:
        response = client.post(
            "/experiments/run",
            json=payload,
        )

    assert response.status_code == 200

    result = response.json()
    evaluation = result["contract_evaluation"]

    assert result["spec"]["contract"]["name"] == ("products-recovery-contract")
    assert evaluation["contract_name"] == ("products-recovery-contract")
    assert evaluation["passed"] is True
    assert len(evaluation["checks"]) == 4

    checks = {(check["phase"], check["metric"]): check for check in evaluation["checks"]}

    assert checks[("baseline", "success_rate")]["observed"] == 1.0

    assert checks[("fault", "fault_rate")]["observed"] == 1.0

    assert checks[("recovery", "success_rate")]["observed"] == 1.0

    assert checks[("recovery", "transport_errors")]["observed"] == 0

    assert all(check["passed"] for check in evaluation["checks"])


def test_experiment_without_contract_returns_no_evaluation() -> None:
    transport = ScriptedProxyTransport()

    app = create_test_app(
        proxy_url="http://proxy",
        transport=transport,
    )

    with TestClient(app) as client:
        response = client.post(
            "/experiments/run",
            json=experiment_payload(),
        )

    assert response.status_code == 200

    result = response.json()

    assert result["spec"]["contract"] is None
    assert result["contract_evaluation"] is None


def test_experiment_returns_failed_contract_evaluation() -> None:
    transport = ScriptedProxyTransport()

    app = create_test_app(
        proxy_url="http://proxy",
        transport=transport,
    )

    payload = experiment_payload(
        requests_per_phase=2,
    )

    payload["contract"] = {
        "name": "fault-tolerance-contract",
        "fault": {
            "min_success_rate": 1.0,
        },
    }

    with TestClient(app) as client:
        response = client.post(
            "/experiments/run",
            json=payload,
        )

    assert response.status_code == 200

    evaluation = response.json()["contract_evaluation"]

    assert evaluation["contract_name"] == "fault-tolerance-contract"
    assert evaluation["passed"] is False
    assert len(evaluation["checks"]) == 1

    check = evaluation["checks"][0]

    assert check["phase"] == "fault"
    assert check["metric"] == "success_rate"
    assert check["operator"] == ">="
    assert check["expected"] == 1.0
    assert check["observed"] == 0.0
    assert check["passed"] is False


def test_experiment_history_endpoints() -> None:
    transport = ScriptedProxyTransport()
    store = MemoryExperimentStore()
    app = build_app(
        proxy_url="http://proxy",
        transport=transport,
        experiment_store=store,
    )

    with TestClient(app) as client:
        run_response = client.post(
            "/experiments/run",
            json=experiment_payload(),
        )

        experiment_id = run_response.json()["experiment_id"]
        list_response = client.get("/experiments?limit=1&offset=0")
        get_response = client.get(f"/experiments/{experiment_id}")
        missing_response = client.get(f"/experiments/{uuid4()}")

    assert run_response.status_code == 200
    assert list_response.status_code == 200
    assert list_response.json()[0]["experiment_id"] == experiment_id
    assert list_response.json()[0]["contract_passed"] is None
    assert get_response.status_code == 200
    assert get_response.json() == run_response.json()
    assert missing_response.status_code == 404
    assert missing_response.json() == {"detail": "Experiment not found"}


def test_experiment_reports_busy_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = ScriptedProxyTransport()
    app = create_test_app(
        proxy_url="http://proxy",
        transport=transport,
    )

    async def reject_run(_: object) -> None:
        from rupturelab.experiments.service import ExperimentBusyError

        raise ExperimentBusyError("Another experiment is already running")

    with TestClient(app) as client:
        monkeypatch.setattr(
            app.state.experiment_service,
            "run",
            reject_run,
        )
        response = client.post(
            "/experiments/run",
            json=experiment_payload(),
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "Another experiment is already running"}
