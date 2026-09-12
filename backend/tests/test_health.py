from uuid import UUID

import httpx2
from fastapi.testclient import TestClient

from rupturelab.experiments.models import ExperimentResult, ExperimentSummary
from rupturelab.main import app, create_app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class UnreadyStore:
    async def ready(self) -> bool:
        return False

    async def save(self, result: ExperimentResult) -> None:
        del result

    async def list_summaries(
        self,
        *,
        limit: int,
        offset: int,
    ) -> list[ExperimentSummary]:
        del limit, offset
        return []

    async def get(self, experiment_id: UUID) -> ExperimentResult | None:
        del experiment_id
        return None


class UnreadyTransport(httpx2.AsyncBaseTransport):
    async def handle_async_request(
        self,
        request: httpx2.Request,
    ) -> httpx2.Response:
        raise httpx2.ConnectError("proxy unavailable", request=request)

    async def aclose(self) -> None:
        return None


def test_readiness_returns_unavailable_dependencies() -> None:
    test_app = create_app(
        proxy_url="http://proxy",
        transport=UnreadyTransport(),
        experiment_store=UnreadyStore(),
    )

    with TestClient(test_app) as test_client:
        response = test_client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": "unavailable",
        "proxy": "unavailable",
    }
