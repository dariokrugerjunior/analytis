"""Use case: score a match using a fitted Dixon-Coles model and persist predictions."""

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.modeling.dixon_coles import score_matrix
from analytis.modeling.markets import (
    btts_probabilities,
    match_result_probabilities,
    over_under_probabilities,
)
from analytis.modeling.persistence import load_params
from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.orm.inference import (
    FeatureSnapshotORM,
    PredictionORM,
)
from analytis.persistence.orm.matches import MatchORM
from analytis.persistence.repositories import ModelVersionRepository
from analytis.persistence.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class ScoreMatchParams:
    match_id: UUID
    model_version_id: UUID
    snapshot_taken_at: datetime | None = None


@dataclass
class ScoreMatchResult:
    predictions_inserted: int
    home_prob: float
    draw_prob: float
    away_prob: float
    over_2_5_prob: float
    btts_yes_prob: float


def _ci(prob: float, n: int = 100) -> tuple[float, float]:
    """Wilson-ish symmetric CI approximation for a probability."""
    se = math.sqrt(max(prob * (1.0 - prob), 1e-9) / n)
    z = 1.96
    low = max(0.0, prob - z * se)
    high = min(1.0, prob + z * se)
    return low, high


class ScoreMatchUseCase:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def execute(self, params: ScoreMatchParams) -> ScoreMatchResult:
        async with UnitOfWork(self._factory) as uow:
            mvrepo = ModelVersionRepository(uow.session)
            model = await mvrepo.get(params.model_version_id)
            if model is None:
                raise ValueError(f"model_version {params.model_version_id} not found")
            if model.artifact_path is None:
                raise ValueError("model has no artifact_path")
            dc_params = load_params(Path(model.artifact_path))

            match = await uow.session.get(MatchORM, params.match_id)
            if match is None:
                raise ValueError(f"match {params.match_id} not found")
            home_team = await uow.session.get(TeamORM, match.home_team_id)
            away_team = await uow.session.get(TeamORM, match.away_team_id)
            if not home_team or not away_team:
                raise ValueError("home or away team missing")

            home_name = home_team.name
            away_name = away_team.name
            if home_name not in dc_params.attack:
                raise ValueError(f"team {home_name!r} not in model")
            if away_name not in dc_params.attack:
                raise ValueError(f"team {away_name!r} not in model")

            ha = 0.0 if match.is_home_neutral else dc_params.home_advantage
            lam_h = math.exp(dc_params.attack[home_name] - dc_params.defense[away_name] + ha)
            lam_a = math.exp(dc_params.attack[away_name] - dc_params.defense[home_name])
            matrix = score_matrix(lam_h, lam_a, dc_params.rho, max_goals=10)

            mr = match_result_probabilities(matrix)
            ou = over_under_probabilities(matrix, line=2.5)
            bt = btts_probabilities(matrix)

            snap_at = params.snapshot_taken_at or datetime.now(UTC)
            existing_snapshot = (
                await uow.session.scalars(
                    select(FeatureSnapshotORM).where(
                        FeatureSnapshotORM.match_id == params.match_id,
                        FeatureSnapshotORM.snapshot_taken_at == snap_at,
                    )
                )
            ).one_or_none()
            if existing_snapshot is not None:
                snapshot_id = existing_snapshot.id
            else:
                snapshot_id = uuid4()
                uow.session.add(
                    FeatureSnapshotORM(
                        id=snapshot_id,
                        match_id=params.match_id,
                        snapshot_taken_at=snap_at,
                        features={
                            "lambda_home": lam_h,
                            "lambda_away": lam_a,
                            "home_advantage_applied": ha,
                        },
                        code_version=str(model.git_sha),
                        created_at=snap_at,
                    )
                )
                await uow.session.flush()

            rows = [
                ("1x2", "home", mr.home),
                ("1x2", "draw", mr.draw),
                ("1x2", "away", mr.away),
                ("over_under_goals", "over_2.5", ou.over),
                ("over_under_goals", "under_2.5", ou.under),
                ("btts", "yes", bt.yes),
                ("btts", "no", bt.no),
            ]
            inserted = 0
            for market, outcome, prob in rows:
                low, high = _ci(prob)
                stmt = (
                    pg_insert(PredictionORM)
                    .values(
                        id=uuid4(),
                        match_id=params.match_id,
                        market=market,
                        outcome=outcome,
                        prob=prob,
                        ci_low=low,
                        ci_high=high,
                        model_version_id=params.model_version_id,
                        feature_snapshot_id=snapshot_id,
                        created_at=snap_at,
                    )
                    .on_conflict_do_nothing(
                        index_elements=[
                            "match_id",
                            "market",
                            "outcome",
                            "model_version_id",
                            "feature_snapshot_id",
                        ]
                    )
                    .returning(PredictionORM.id)
                )
                result = await uow.session.execute(stmt)
                if result.scalar() is not None:
                    inserted += 1

        return ScoreMatchResult(
            predictions_inserted=inserted,
            home_prob=mr.home,
            draw_prob=mr.draw,
            away_prob=mr.away,
            over_2_5_prob=ou.over,
            btts_yes_prob=bt.yes,
        )
