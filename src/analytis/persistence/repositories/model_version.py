"""Repository for ModelVersion."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.persistence.orm.inference import ModelVersionORM


class ModelVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(
        self,
        *,
        name: str,
        family: str,
        git_sha: str,
        hyperparams: dict[str, Any],
        metrics: dict[str, Any] | None = None,
        artifact_path: str | None = None,
        trained_at: datetime | None = None,
        is_promoted: bool = False,
    ) -> UUID:
        version_id = uuid4()
        self._session.add(
            ModelVersionORM(
                id=version_id,
                name=name,
                family=family,
                git_sha=git_sha,
                hyperparams=hyperparams,
                metrics=metrics or {},
                artifact_path=artifact_path,
                trained_at=trained_at,
                is_promoted=is_promoted,
            )
        )
        return version_id

    async def get(self, version_id: UUID) -> ModelVersionORM | None:
        result = await self._session.scalars(
            select(ModelVersionORM).where(ModelVersionORM.id == version_id)
        )
        return result.one_or_none()

    async def get_by_name(self, name: str) -> ModelVersionORM | None:
        result = await self._session.scalars(
            select(ModelVersionORM).where(ModelVersionORM.name == name)
        )
        return result.one_or_none()
