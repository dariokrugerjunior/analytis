"""Use case: train an XGBoost match classifier from features built over
finished matches in the DB and persist it as a ModelVersion."""

import pickle
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.features.builder import FeatureBuilder
from analytis.modeling.persistence import DEFAULT_MODELS_DIR
from analytis.modeling.xgboost_classifier import XGBoostMatchClassifier
from analytis.persistence.orm.matches import MatchORM
from analytis.persistence.repositories import (
    MatchRepository,
    ModelVersionRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class TrainXGBoostParams:
    since: datetime
    name: str
    market: str = "1x2"
    n_estimators: int = 200
    max_depth: int = 4
    learning_rate: float = 0.05


@dataclass
class TrainXGBoostResult:
    version_id: str
    artifact_path: str
    n_samples: int
    n_features: int


def _git_sha() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.STDOUT)
        return out.decode().strip()[:12]
    except Exception:
        return "unknown"


class TrainXGBoostUseCase:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        models_dir: Path | None = None,
    ) -> None:
        self._factory = session_factory
        self._models_dir = models_dir or DEFAULT_MODELS_DIR

    async def execute(self, params: TrainXGBoostParams) -> TrainXGBoostResult:
        # 1. Pull finished matches and build feature dicts.
        async with UnitOfWork(self._factory) as uow:
            matches = list(
                (
                    await uow.session.scalars(
                        select(MatchORM)
                        .where(
                            MatchORM.status == "finished",
                            MatchORM.kickoff_utc >= params.since,
                            MatchORM.home_goals.is_not(None),
                            MatchORM.away_goals.is_not(None),
                        )
                        .order_by(MatchORM.kickoff_utc.asc())
                    )
                ).all()
            )

            features: list[dict[str, object]] = []
            outcomes: list[tuple[int, int]] = []
            builder = FeatureBuilder(MatchRepository(uow.session))
            for orm in matches:
                if orm.home_goals is None or orm.away_goals is None:
                    continue
                # Map ORM -> domain Match minimal subset that builder uses
                from analytis.domain.match import Match, MatchStatus

                domain_match = Match(
                    id=orm.id,
                    season_id=orm.season_id,
                    home_team_id=orm.home_team_id,
                    away_team_id=orm.away_team_id,
                    kickoff_utc=orm.kickoff_utc,
                    is_home_neutral=orm.is_home_neutral,
                    status=MatchStatus.FINISHED,
                    home_goals=orm.home_goals,
                    away_goals=orm.away_goals,
                    home_corners=orm.home_corners,
                    away_corners=orm.away_corners,
                    external_ids=dict(orm.external_ids) or {"_": str(orm.id)},
                )
                feat = await builder.build(domain_match, as_of=orm.kickoff_utc)
                features.append(feat)
                outcomes.append((int(orm.home_goals), int(orm.away_goals)))

        if not features:
            raise ValueError("no finished matches in the given window")

        # 2. Train classifier.
        clf = XGBoostMatchClassifier(
            market=params.market,
            n_estimators=params.n_estimators,
            max_depth=params.max_depth,
            learning_rate=params.learning_rate,
        )
        clf.fit(features, outcomes)

        # 3. Persist ModelVersion + pickle.
        async with UnitOfWork(self._factory) as uow:
            repo = ModelVersionRepository(uow.session)
            vid = await repo.insert(
                name=params.name,
                family="xgboost",
                git_sha=_git_sha(),
                hyperparams={
                    "market": params.market,
                    "n_estimators": params.n_estimators,
                    "max_depth": params.max_depth,
                    "learning_rate": params.learning_rate,
                    "since": params.since.isoformat(),
                },
                metrics={
                    "n_samples": len(features),
                },
                trained_at=datetime.now(UTC),
            )

        self._models_dir.mkdir(parents=True, exist_ok=True)
        artifact = self._models_dir / f"{vid}.pkl"
        with artifact.open("wb") as fh:
            pickle.dump(clf, fh)

        async with UnitOfWork(self._factory) as uow:
            mv_orm = await ModelVersionRepository(uow.session).get(vid)
            assert mv_orm is not None
            mv_orm.artifact_path = str(artifact)

        return TrainXGBoostResult(
            version_id=str(vid),
            artifact_path=str(artifact),
            n_samples=len(features),
            n_features=len(clf._vectoriser.feature_names),
        )
