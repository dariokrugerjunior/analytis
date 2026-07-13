"""Unit tests for the SPA static-file fallback used to serve the frontend."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from analytis.api.main import SPAStaticFiles


@pytest.fixture
def spa_client(tmp_path: Path) -> TestClient:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>analytis-spa</title>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('hi')", encoding="utf-8")

    app = FastAPI()

    @app.get("/v1/ping")
    async def _ping() -> dict[str, bool]:
        return {"ok": True}

    app.mount("/", SPAStaticFiles(directory=str(dist), html=True), name="frontend")
    return TestClient(app)


def test_root_serves_index(spa_client: TestClient) -> None:
    resp = spa_client.get("/")
    assert resp.status_code == 200
    assert "analytis-spa" in resp.text


def test_client_route_falls_back_to_index(spa_client: TestClient) -> None:
    # A client-side route with no file on disk must serve index.html, not 404.
    for route in ("/jogos", "/acertos", "/matches/some-uuid"):
        resp = spa_client.get(route)
        assert resp.status_code == 200, route
        assert "analytis-spa" in resp.text


def test_real_asset_served_directly(spa_client: TestClient) -> None:
    resp = spa_client.get("/assets/app.js")
    assert resp.status_code == 200
    assert "console.log" in resp.text


def test_api_route_still_returns_json(spa_client: TestClient) -> None:
    resp = spa_client.get("/v1/ping")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_unknown_api_path_stays_404(spa_client: TestClient) -> None:
    # /v1/* must NOT fall back to index.html — API 404s stay 404s.
    resp = spa_client.get("/v1/does-not-exist")
    assert resp.status_code == 404
    assert "analytis-spa" not in resp.text
