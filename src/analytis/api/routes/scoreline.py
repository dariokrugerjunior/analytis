"""Scoreline grid derived from the ensemble model's 1X2 + OU 2.5 marginals.

The ensemble doesn't natively produce a scoreline distribution, so we fit an
independent-Poisson score grid whose marginals reproduce the ensemble's
P(home win) and P(over 2.5). This gives a coherent "most likely score" view
that never contradicts the 1X2 bars on the same page.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.api.deps import require_api_key
from analytis.config import Settings, get_settings
from analytis.modeling.ensemble_scoreline import derive_lambdas, score_matrix
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.orm.inference import ModelVersionORM, PredictionORM
from analytis.persistence.orm.matches import MatchORM

router = APIRouter(prefix="/matches", tags=["scoreline"])

CANONICAL_MODEL = "ensemble-v1"


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


async def _load_ensemble_predictions(
    session: AsyncSession, match_id: UUID
) -> dict[str, dict[str, float]]:
    """Return {market: {outcome: prob}} for the canonical model, or empty dict."""
    stmt = (
        select(PredictionORM)
        .join(ModelVersionORM, PredictionORM.model_version_id == ModelVersionORM.id)
        .where(
            PredictionORM.match_id == match_id,
            ModelVersionORM.name == CANONICAL_MODEL,
        )
    )
    rows = list((await session.scalars(stmt)).all())
    preds: dict[str, dict[str, float]] = {}
    for p in rows:
        preds.setdefault(p.market, {})[p.outcome] = p.prob
    return preds


@router.get(
    "/{match_id}/scoreline-grid",
    response_model=ScorelineGridResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_scoreline_grid(
    match_id: UUID,
    max_goals: int = Query(6, ge=2, le=10),
    top: int = Query(8, ge=1, le=25),
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

        preds = await _load_ensemble_predictions(session, match_id)

    onex2 = preds.get("1x2") or {}
    ou = preds.get("over_under_goals") or {}
    p_home_win = onex2.get("home")
    p_over_2_5 = ou.get("over_2.5")
    if p_home_win is None or p_over_2_5 is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "Placar exato indisponível: o ensemble não tem 1X2 + OU 2.5 gravado para "
                "esta partida."
            ),
        )

    lam_h, lam_a = derive_lambdas(p_home_win, p_over_2_5, max_goals=max_goals)
    matrix = score_matrix(lam_h, lam_a, max_goals=max_goals)

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
        model_version=CANONICAL_MODEL,
        max_goals=max_goals,
        lambda_home=lam_h,
        lambda_away=lam_a,
        grid=[[float(matrix[i, j]) for j in range(max_goals + 1)] for i in range(max_goals + 1)],
        top_scorelines=flat[:top],
        most_likely=flat[0],
    )
