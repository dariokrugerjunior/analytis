"""Web push endpoints — vapid public key + subscribe."""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from analytis.config import Settings, get_settings
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.persistence.repositories.push_subscription import (
    PushSubscriptionRecord,
    PushSubscriptionRepository,
)

router = APIRouter(prefix="/push", tags=["push"])

_ALLOWED_HOSTS = {
    "fcm.googleapis.com",
    "updates.push.services.mozilla.com",
    "web.push.apple.com",
}


def _is_allowed_endpoint(endpoint: str) -> bool:
    try:
        host = urlparse(endpoint).hostname or ""
    except ValueError:
        return False
    if host in _ALLOWED_HOSTS:
        return True
    return bool(host.endswith(".notify.windows.com"))


class VapidPublicKeyResponse(BaseModel):
    public_key: str


class SubscribeRequest(BaseModel):
    endpoint: str = Field(min_length=10)
    p256dh: str = Field(min_length=1)
    auth: str = Field(min_length=1)
    user_agent: str | None = None


@router.get("/vapid-public-key", response_model=VapidPublicKeyResponse)
async def get_vapid_public_key(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> VapidPublicKeyResponse:
    if not settings.vapid_public_key:
        raise HTTPException(status_code=503, detail="VAPID public key not configured on server")
    return VapidPublicKeyResponse(public_key=settings.vapid_public_key)


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe(
    body: SubscribeRequest,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> dict[str, str]:
    if not _is_allowed_endpoint(body.endpoint):
        raise HTTPException(status_code=400, detail="endpoint host not in allowlist")

    engine = create_engine(settings)
    try:
        factory = create_session_factory(engine)
        async with factory() as session:
            repo = PushSubscriptionRepository(session)
            await repo.upsert(
                PushSubscriptionRecord(
                    endpoint=body.endpoint,
                    p256dh=body.p256dh,
                    auth=body.auth,
                    user_agent=body.user_agent,
                )
            )
            await session.commit()
    finally:
        await engine.dispose()
    return {"status": "ok"}
