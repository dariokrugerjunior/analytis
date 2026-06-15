"""Routes for exact-scoreline probability grids (Dixon-Coles)."""

import math
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.api.deps import require_api_key
from analytis.config import Settings, get_settings
from analytis.modeling.dixon_coles import score_matrix
from analytis.modeling.persistence import load_params
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.orm.inference import ModelVersionORM, PredictionORM
from analytis.persistence.orm.matches import MatchORM

router = APIRouter(prefix="/matches", tags=["scoreline"])


@asynccontextmanager
async def _session(settings: Settings) -> AsyncIterator[AsyncSession]:
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


class ScorelineItem(BaseModel):
    home: int
    away: int
    prob: float


class ScorelineGridResponse(BaseModel):
    match_id: UUID
    home_team: str
    away_team: str
    model_version: str
    max_goals: int
    lambda_home: float
    lambda_away: float
    grid: list[list[float]]
    top_scorelines: list[ScorelineItem]
    most_likely: ScorelineItem


async def _resolve_dc_model(
    session: AsyncSession, match_id: UUID, model_name: str | None
) -> ModelVersionORM:
    if model_name:
        stmt = select(ModelVersionORM).where(
            ModelVersionORM.name == model_name,
            ModelVersionORM.family == "dixon-coles",
        )
        model = (await session.scalars(stmt)).one_or_none()
        if model is None:
            raise HTTPException(
                status_code=404, detail=f"dixon-coles model {model_name!r} not found"
            )
        return model

    stmt = (
        select(ModelVersionORM)
        .join(PredictionORM, PredictionORM.model_version_id == ModelVersionORM.id)
        .where(
            PredictionORM.match_id == match_id,
            ModelVersionORM.family == "dixon-coles",
        )
        .order_by(PredictionORM.created_at.desc())
        .limit(1)
    )
    model = (await session.scalars(stmt)).first()
    if model is not None:
        return model

    stmt = (
        select(ModelVersionORM)
        .where(ModelVersionORM.family == "dixon-coles")
        .order_by(ModelVersionORM.trained_at.desc())
        .limit(1)
    )
    model = (await session.scalars(stmt)).first()
    if model is None:
        raise HTTPException(status_code=404, detail="no dixon-coles model available")
    return model


@router.get(
    "/{match_id}/scoreline-grid",
    response_model=ScorelineGridResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_scoreline_grid(
    match_id: UUID,
    max_goals: int = Query(6, ge=2, le=10),
    top: int = Query(8, ge=1, le=25),
    model: str | None = Query(None, description="Optional DC model name override"),
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> ScorelineGridResponse:
    async with _session(settings) as session:
        match = await session.get(MatchORM, match_id)
        if match is None:
            raise HTTPException(status_code=404, detail="match not found")
        home_team = await session.get(TeamORM, match.home_team_id)
        away_team = await session.get(TeamORM, match.away_team_id)
        if not home_team or not away_team:
            raise HTTPException(status_code=500, detail="team metadata missing")

        model_row = await _resolve_dc_model(session, match_id, model)
        if model_row.artifact_path is None:
            raise HTTPException(status_code=500, detail="model has no artifact_path")
        dc_params = load_params(Path(model_row.artifact_path))

        if home_team.name not in dc_params.attack:
            raise HTTPException(status_code=422, detail=f"team {home_team.name!r} not in model")
        if away_team.name not in dc_params.attack:
            raise HTTPException(status_code=422, detail=f"team {away_team.name!r} not in model")

        ha = 0.0 if match.is_home_neutral else dc_params.home_advantage
        lam_h = math.exp(dc_params.attack[home_team.name] - dc_params.defense[away_team.name] + ha)
        lam_a = math.exp(dc_params.attack[away_team.name] - dc_params.defense[home_team.name])
        matrix = score_matrix(lam_h, lam_a, dc_params.rho, max_goals=max_goals)

    flat = [
        ScorelineItem(home=i, away=j, prob=float(matrix[i, j]))
        for i in range(max_goals + 1)
        for j in range(max_goals + 1)
    ]
    flat.sort(key=lambda s: s.prob, reverse=True)

    return ScorelineGridResponse(
        match_id=match.id,
        home_team=home_team.name,
        away_team=away_team.name,
        model_version=model_row.name,
        max_goals=max_goals,
        lambda_home=float(lam_h),
        lambda_away=float(lam_a),
        grid=[[float(matrix[i, j]) for j in range(max_goals + 1)] for i in range(max_goals + 1)],
        top_scorelines=flat[:top],
        most_likely=flat[0],
    )
