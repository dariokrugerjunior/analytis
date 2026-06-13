"""Use case: score a match using a weighted average of Dixon-Coles + XGBoost.

This is a simpler-than-stacking ensembler: it averages the two component
probabilities per outcome with configurable weights, then renormalises.
Persists predictions as a separate ModelVersion (family="ensemble").
"""

import math
import pickle
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.features.builder import FeatureBuilder
from analytis.modeling.dixon_coles import score_matrix
from analytis.modeling.markets import (
    btts_probabilities,
    match_result_probabilities,
    over_under_probabilities,
)
from analytis.modeling.persistence import load_params
from analytis.modeling.xgboost_classifier import XGBoostMatchClassifier
from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.orm.inference import (
    FeatureSnapshotORM,
    PredictionORM,
)
from analytis.persistence.orm.matches import MatchORM
from analytis.persistence.repositories import (
    MatchRepository,
    ModelVersionRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class ScoreEnsembleParams:
    match_id: UUID
    dc_model_version_id: UUID
    xgb_model_version_id: UUID
    ensemble_model_version_id: UUID
    dc_weight: float = 0.5
    xgb_weight: float = 0.5
    snapshot_taken_at: datetime | None = None


@dataclass
class ScoreEnsembleResult:
    predictions_inserted: int
    home_prob: float
    draw_prob: float
    away_prob: float


def _ci(prob: float, n: int = 100) -> tuple[float, float]:
    se = math.sqrt(max(prob * (1.0 - prob), 1e-9) / n)
    z = 1.96
    return max(0.0, prob - z * se), min(1.0, prob + z * se)


def _normalise(d: dict[str, float]) -> dict[str, float]:
    total = sum(d.values())
    if total <= 0:
        return d
    return {k: v / total for k, v in d.items()}


class ScoreEnsembleUseCase:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def execute(self, params: ScoreEnsembleParams) -> ScoreEnsembleResult:
        # 1. Load both models from disk.
        async with UnitOfWork(self._factory) as uow:
            mvrepo = ModelVersionRepository(uow.session)
            dc_mv = await mvrepo.get(params.dc_model_version_id)
            xgb_mv = await mvrepo.get(params.xgb_model_version_id)
            if dc_mv is None or xgb_mv is None:
                raise ValueError("DC or XGB model version not found")
            if dc_mv.artifact_path is None or xgb_mv.artifact_path is None:
                raise ValueError("model artifact_path missing")
            dc_params = load_params(Path(dc_mv.artifact_path))
            with Path(xgb_mv.artifact_path).open("rb") as fh:
                xgb_clf: XGBoostMatchClassifier = pickle.load(fh)

            match = await uow.session.get(MatchORM, params.match_id)
            if match is None:
                raise ValueError(f"match {params.match_id} not found")
            home_team = await uow.session.get(TeamORM, match.home_team_id)
            away_team = await uow.session.get(TeamORM, match.away_team_id)
            if home_team is None or away_team is None:
                raise ValueError("home or away team missing")

        # 2. Compute DC probabilities.
        home_name = home_team.name
        away_name = away_team.name
        if home_name not in dc_params.attack or away_name not in dc_params.attack:
            raise ValueError("team not in DC params")
        ha = 0.0 if match.is_home_neutral else dc_params.home_advantage
        lam_h = math.exp(dc_params.attack[home_name] - dc_params.defense[away_name] + ha)
        lam_a = math.exp(dc_params.attack[away_name] - dc_params.defense[home_name])
        matrix = score_matrix(lam_h, lam_a, dc_params.rho, max_goals=10)
        mr = match_result_probabilities(matrix)
        ou = over_under_probabilities(matrix, line=2.5)
        bt = btts_probabilities(matrix)
        dc_1x2 = {"home": mr.home, "draw": mr.draw, "away": mr.away}

        # 3. Compute XGBoost probabilities (build features for this match).
        async with UnitOfWork(self._factory) as uow:
            from analytis.domain.match import Match, MatchStatus

            domain_match = Match(
                id=match.id,
                season_id=match.season_id,
                home_team_id=match.home_team_id,
                away_team_id=match.away_team_id,
                kickoff_utc=match.kickoff_utc,
                is_home_neutral=match.is_home_neutral,
                status=MatchStatus(match.status),
                home_goals=match.home_goals,
                away_goals=match.away_goals,
                home_corners=match.home_corners,
                away_corners=match.away_corners,
                external_ids=dict(match.external_ids) or {"_": str(match.id)},
            )
            builder = FeatureBuilder(MatchRepository(uow.session))
            features = await builder.build(domain_match, as_of=match.kickoff_utc)

        xgb_1x2 = xgb_clf.predict_proba_one(features)

        # 4. Weighted ensemble (only 1x2 for now; OU/BTTS just from DC).
        w_dc, w_xgb = params.dc_weight, params.xgb_weight
        ens_1x2 = _normalise(
            {k: w_dc * dc_1x2[k] + w_xgb * xgb_1x2.get(k, 0.0) for k in ("home", "draw", "away")}
        )

        # 5. Persist snapshot + predictions.
        snap_at = params.snapshot_taken_at or datetime.now(UTC)
        async with UnitOfWork(self._factory) as uow:
            existing_snap = (
                await uow.session.scalars(
                    select(FeatureSnapshotORM).where(
                        FeatureSnapshotORM.match_id == params.match_id,
                        FeatureSnapshotORM.snapshot_taken_at == snap_at,
                    )
                )
            ).one_or_none()
            if existing_snap is None:
                snapshot_id = uuid4()
                uow.session.add(
                    FeatureSnapshotORM(
                        id=snapshot_id,
                        match_id=params.match_id,
                        snapshot_taken_at=snap_at,
                        features={
                            "lambda_home": lam_h,
                            "lambda_away": lam_a,
                            "dc_weight": w_dc,
                            "xgb_weight": w_xgb,
                            **features,
                        },
                        code_version="ensemble-v0.1",
                        created_at=snap_at,
                    )
                )
                await uow.session.flush()
            else:
                snapshot_id = existing_snap.id

            rows: list[tuple[str, str, float]] = [
                ("1x2", "home", ens_1x2["home"]),
                ("1x2", "draw", ens_1x2["draw"]),
                ("1x2", "away", ens_1x2["away"]),
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
                        model_version_id=params.ensemble_model_version_id,
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

        return ScoreEnsembleResult(
            predictions_inserted=inserted,
            home_prob=ens_1x2["home"],
            draw_prob=ens_1x2["draw"],
            away_prob=ens_1x2["away"],
        )
