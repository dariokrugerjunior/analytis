"""Integration tests for /v1/push/* routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.api.main import create_app
from analytis.persistence.orm.push import PushSubscriptionORM

VALID_BODY = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/abc",
    "p256dh": "p256dh-base64",
    "auth": "auth-base64",
    "user_agent": "Mozilla/5.0",
}


@pytest.mark.integration
def test_get_vapid_public_key_returns_200_no_auth(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANALYTIS_VAPID_PUBLIC_KEY", "test-pub-key")
    monkeypatch.setenv("ANALYTIS_VAPID_PRIVATE_KEY", "test-priv-key")
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/push/vapid-public-key")
    assert resp.status_code == 200
    assert resp.json() == {"public_key": "test-pub-key"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_subscribe_creates_row(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.post("/v1/push/subscribe", json=VALID_BODY)
    assert resp.status_code == 201

    async with session_factory() as session:
        rows = (await session.scalars(select(PushSubscriptionORM))).all()
        assert any(r.endpoint == VALID_BODY["endpoint"] for r in rows)


@pytest.mark.integration
def test_subscribe_rejects_invalid_host(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app = create_app()
    client = TestClient(app)
    body = {**VALID_BODY, "endpoint": "https://evil.example.com/spam"}
    resp = client.post("/v1/push/subscribe", json=body)
    assert resp.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_subscribe_same_endpoint_twice_updates(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app = create_app()
    client = TestClient(app)
    body1 = {**VALID_BODY, "endpoint": "https://fcm.googleapis.com/fcm/send/twice"}
    client.post("/v1/push/subscribe", json=body1)
    body2 = {**body1, "p256dh": "different-p256dh"}
    resp = client.post("/v1/push/subscribe", json=body2)
    assert resp.status_code == 201

    async with session_factory() as session:
        rows = (
            await session.scalars(
                select(PushSubscriptionORM).where(PushSubscriptionORM.endpoint == body1["endpoint"])
            )
        ).all()
        assert len(rows) == 1
        assert rows[0].p256dh == "different-p256dh"
