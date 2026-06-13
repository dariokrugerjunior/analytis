"""Repository for FeatureSnapshot persistence."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.persistence.orm.inference import FeatureSnapshotORM


class FeatureSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(
        self,
        match_id: UUID,
        snapshot_taken_at: datetime,
        features: dict[str, Any],
        *,
        code_version: str | None = None,
    ) -> UUID:
        from uuid import uuid4

        from analytis.persistence.orm.base import utcnow

        snapshot_id = uuid4()
        self._session.add(
            FeatureSnapshotORM(
                id=snapshot_id,
                match_id=match_id,
                snapshot_taken_at=snapshot_taken_at,
                features=features,
                code_version=code_version,
                created_at=utcnow(),
            )
        )
        return snapshot_id

    async def get(self, snapshot_id: UUID) -> FeatureSnapshotORM | None:
        result = await self._session.scalars(
            select(FeatureSnapshotORM).where(FeatureSnapshotORM.id == snapshot_id)
        )
        return result.one_or_none()
