"""Integration tests for /v1/matches?upcoming=true route."""

import pytest
from fastapi.testclient import TestClient

from analytis.api.main import create_app
from analytis.config import get_settings


@pytest.mark.integration
def test_upcoming_matches_requires_api_key() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/matches?upcoming=true&days=7")
    assert resp.status_code == 401


@pytest.mark.integration
def test_upcoming_matches_returns_items_shape() -> None:
    api_key = get_settings().api_key.get_secret_value()
    app = create_app()
    client = TestClient(app)
    resp = client.get(
        "/v1/matches?upcoming=true&days=7",
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert isinstance(body["items"], list)
    if body["items"]:
        first = body["items"][0]
        assert "id" in first
        assert "home_team" in first
        assert "away_team" in first
        assert "kickoff_utc" in first
        assert "status" in first
