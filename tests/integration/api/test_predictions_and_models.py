"""Integration tests for /v1/matches/{id}/predictions and /v1/models."""

import pytest
from fastapi.testclient import TestClient

from analytis.api.main import create_app


@pytest.mark.integration
def test_models_returns_list() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/models")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert isinstance(body["items"], list)


@pytest.mark.integration
def test_predictions_unknown_match_returns_404() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get(
        "/v1/matches/00000000-0000-0000-0000-000000000000/predictions",
    )
    assert resp.status_code == 404
