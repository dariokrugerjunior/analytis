"""Smoke tests for the health endpoint."""

import pytest
from fastapi.testclient import TestClient

from analytis.api.main import create_app


@pytest.mark.integration
def test_health_returns_ok() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "analytis"
