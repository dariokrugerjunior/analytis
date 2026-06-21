"""Repository for push_subscription table."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.persistence.orm.push import PushSubscriptionORM


@dataclass(frozen=True)
class PushSubscriptionRecord:
    endpoint: str
    p256dh: str
    auth: str
    user_agent: str | None


class PushSubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, sub: PushSubscriptionRecord) -> None:
        """Insert; on endpoint conflict, update last_seen_at + keys."""
        stmt = pg_insert(PushSubscriptionORM).values(
            endpoint=sub.endpoint,
            p256dh=sub.p256dh,
            auth=sub.auth,
            user_agent=sub.user_agent,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["endpoint"],
            set_={
                "p256dh": stmt.excluded.p256dh,
                "auth": stmt.excluded.auth,
                "user_agent": stmt.excluded.user_agent,
                "last_seen_at": sa_text("NOW()"),
            },
        )
        await self._session.execute(stmt)

    async def delete_by_endpoint(self, endpoint: str) -> None:
        await self._session.execute(
            delete(PushSubscriptionORM).where(PushSubscriptionORM.endpoint == endpoint)
        )

    async def list_all(self) -> list[PushSubscriptionORM]:
        result = await self._session.scalars(select(PushSubscriptionORM))
        return list(result.all())
