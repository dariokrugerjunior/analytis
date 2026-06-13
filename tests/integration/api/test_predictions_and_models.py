"""Integration tests for /v1/matches/{id}/predictions and /v1/models."""

import os

import pytest
from fastapi.testclient import TestClient

from analytis.api.main import create_app


@pytest.mark.integration
def test_predictions_requires_api_key() -> None:
    app = create_app()
    client = TestClient(app)
    # No API key header → 401
    resp = client.get("/v1/matches/00000000-0000-0000-0000-000000000000/predictions")
    assert resp.status_code == 401


@pytest.mark.integration
def test_models_requires_api_key() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/models")
    assert resp.status_code == 401


@pytest.mark.integration
def test_models_with_api_key_returns_list() -> None:
    api_key = os.environ.get("ANALYTIS_API_KEY", "local-dev")
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/models", headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert isinstance(body["items"], list)


@pytest.mark.integration
def test_predictions_unknown_match_returns_404() -> None:
    api_key = os.environ.get("ANALYTIS_API_KEY", "local-dev")
    app = create_app()
    client = TestClient(app)
    resp = client.get(
        "/v1/matches/00000000-0000-0000-0000-000000000000/predictions",
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 404
