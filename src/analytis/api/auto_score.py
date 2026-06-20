"""On-demand scoring fallback for the predictions endpoint.

When a match has no persisted predictions, pick the most recent Dixon-Coles
model whose roster covers both teams and score the match through the same
use case the CLI uses. Idempotent — re-runs are safe (predictions table has
a unique constraint and the use case already uses ON CONFLICT DO NOTHING).
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.application.score_match import ScoreMatchParams, ScoreMatchUseCase
from analytis.modeling.fitting import DixonColesParams
from analytis.modeling.persistence import load_params
from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.orm.inference import ModelVersionORM
from analytis.persistence.orm.matches import MatchORM

log = structlog.get_logger(__name__)

_PARAMS_CACHE: dict[tuple[str, float], DixonColesParams] = {}


def _load_cached(artifact_path: str) -> DixonColesParams | None:
    p = Path(artifact_path)
    if not p.exists():
        return None
    key = (artifact_path, p.stat().st_mtime)
    cached = _PARAMS_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        params = load_params(p)
    except Exception as exc:
        log.warning("auto_score_load_failed", artifact=artifact_path, error=str(exc))
        return None
    _PARAMS_CACHE[key] = params
    return params


async def _find_dc_model_covering(
    session: AsyncSession, home_name: str, away_name: str
) -> ModelVersionORM | None:
    stmt = (
        select(ModelVersionORM)
        .where(
            ModelVersionORM.family == "dixon-coles",
            ModelVersionORM.artifact_path.is_not(None),
        )
        .order_by(ModelVersionORM.trained_at.desc().nullslast())
    )
    rows = (await session.scalars(stmt)).all()
    for model in rows:
        if model.artifact_path is None:
            continue
        params = _load_cached(model.artifact_path)
        if params is None:
            continue
        if home_name in params.attack and away_name in params.attack:
            return model
    return None


async def auto_score_if_missing(
    session_factory: async_sessionmaker[AsyncSession],
    match_id: UUID,
) -> ModelVersionORM | None:
    """Score `match_id` with the broadest covering DC model.

    Returns the model used, or None when no DC model covers both teams.
    Safe to call when predictions already exist (no-ops via the use case's
    ON CONFLICT DO NOTHING).
    """
    async with session_factory() as session:
        match = await session.get(MatchORM, match_id)
        if match is None:
            return None
        home = await session.get(TeamORM, match.home_team_id)
        away = await session.get(TeamORM, match.away_team_id)
        if home is None or away is None:
            return None
        home_name = home.name
        away_name = away.name
        model = await _find_dc_model_covering(session, home_name, away_name)
        model_id = model.id if model else None
        model_name = model.name if model else None

    if model is None or model_id is None:
        log.info(
            "auto_score_no_model",
            match_id=str(match_id),
            home=home_name,
            away=away_name,
        )
        return None

    try:
        await ScoreMatchUseCase(session_factory).execute(
            ScoreMatchParams(match_id=match_id, model_version_id=model_id)
        )
    except ValueError as exc:
        log.warning(
            "auto_score_failed",
            match_id=str(match_id),
            model=model_name,
            error=str(exc),
        )
        return None
    log.info(
        "auto_score_applied",
        match_id=str(match_id),
        model=model_name,
        home=home_name,
        away=away_name,
    )
    return model


__all__ = ["auto_score_if_missing"]
