"""Routes for trained model versions."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.api.deps import require_api_key
from analytis.config import Settings, get_settings
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.persistence.orm.inference import ModelVersionORM

router = APIRouter(prefix="/models", tags=["models"])


@asynccontextmanager
async def _session(settings: Settings) -> AsyncIterator[AsyncSession]:
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


class ModelVersionResponse(BaseModel):
    id: UUID
    name: str
    family: str
    git_sha: str
    hyperparams: dict[str, Any]
    metrics: dict[str, Any]
    artifact_path: str | None
    trained_at: datetime | None
    is_promoted: bool


class ModelVersionListResponse(BaseModel):
    items: list[ModelVersionResponse]


@router.get(
    "",
    response_model=ModelVersionListResponse,
    dependencies=[Depends(require_api_key)],
)
async def list_models(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> ModelVersionListResponse:
    async with _session(settings) as session:
        rows = (
            await session.scalars(
                select(ModelVersionORM).order_by(ModelVersionORM.trained_at.desc().nullslast())
            )
        ).all()
        return ModelVersionListResponse(
            items=[
                ModelVersionResponse(
                    id=m.id,
                    name=m.name,
                    family=m.family,
                    git_sha=m.git_sha,
                    hyperparams=dict(m.hyperparams),
                    metrics=dict(m.metrics),
                    artifact_path=m.artifact_path,
                    trained_at=m.trained_at,
                    is_promoted=m.is_promoted,
                )
                for m in rows
            ]
        )


@router.get(
    "/{version_id}/metrics",
    response_model=ModelVersionResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_model_metrics(
    version_id: UUID,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> ModelVersionResponse:
    async with _session(settings) as session:
        m = await session.get(ModelVersionORM, version_id)
        if m is None:
            raise HTTPException(status_code=404, detail="model not found")
        return ModelVersionResponse(
            id=m.id,
            name=m.name,
            family=m.family,
            git_sha=m.git_sha,
            hyperparams=dict(m.hyperparams),
            metrics=dict(m.metrics),
            artifact_path=m.artifact_path,
            trained_at=m.trained_at,
            is_promoted=m.is_promoted,
        )
