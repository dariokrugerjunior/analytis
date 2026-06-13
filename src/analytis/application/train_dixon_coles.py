"""Use case: train a Dixon-Coles model from finished matches in the DB."""

import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.modeling.fitting import (
    FitConfig,
    MatchObservation,
    fit_dixon_coles,
)
from analytis.modeling.persistence import DEFAULT_MODELS_DIR, save_params
from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.orm.matches import MatchORM
from analytis.persistence.repositories import ModelVersionRepository
from analytis.persistence.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class TrainDixonColesParams:
    since: datetime
    name: str
    max_iter: int = 200
    decay_per_day: float = 0.005


@dataclass
class TrainDixonColesResult:
    version_id: str
    artifact_path: str
    team_count: int
    match_count: int
    home_advantage: float
    rho: float


def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.STDOUT,
        )
        return out.decode().strip()[:12]
    except Exception:
        return "unknown"


class TrainDixonColesUseCase:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        models_dir: Path | None = None,
    ) -> None:
        self._factory = session_factory
        self._models_dir = models_dir or DEFAULT_MODELS_DIR

    async def execute(self, params: TrainDixonColesParams) -> TrainDixonColesResult:
        async with UnitOfWork(self._factory) as uow:
            stmt = (
                select(MatchORM)
                .where(
                    MatchORM.status == "finished",
                    MatchORM.kickoff_utc >= params.since,
                    MatchORM.home_goals.is_not(None),
                    MatchORM.away_goals.is_not(None),
                )
                .order_by(MatchORM.kickoff_utc.asc())
            )
            rows = (await uow.session.scalars(stmt)).all()

            team_stmt = select(TeamORM.id, TeamORM.name)
            id_to_name: dict[UUID, str] = {
                row.id: row.name for row in (await uow.session.execute(team_stmt)).all()
            }

            observations: list[MatchObservation] = []
            for m in rows:
                home_name = id_to_name.get(m.home_team_id)
                away_name = id_to_name.get(m.away_team_id)
                if not home_name or not away_name:
                    continue
                if m.home_goals is None or m.away_goals is None:
                    continue
                observations.append(
                    MatchObservation(
                        home_team=home_name,
                        away_team=away_name,
                        home_goals=int(m.home_goals),
                        away_goals=int(m.away_goals),
                        kickoff_utc=m.kickoff_utc,
                        is_neutral=m.is_home_neutral,
                    )
                )

        if not observations:
            raise ValueError("no finished matches found in the given window")

        fit = fit_dixon_coles(
            observations,
            config=FitConfig(
                max_iter=params.max_iter,
                decay_per_day=params.decay_per_day,
            ),
        )

        async with UnitOfWork(self._factory) as uow:
            repo = ModelVersionRepository(uow.session)
            vid = await repo.insert(
                name=params.name,
                family="dixon-coles",
                git_sha=_git_sha(),
                hyperparams={
                    "max_iter": params.max_iter,
                    "decay_per_day": params.decay_per_day,
                    "since": params.since.isoformat(),
                },
                metrics={
                    "n_matches": len(observations),
                    "n_teams": len(fit.attack),
                    "home_advantage": fit.home_advantage,
                    "rho": fit.rho,
                },
                trained_at=datetime.now(UTC),
            )

        artifact = save_params(fit, vid, models_dir=self._models_dir)

        async with UnitOfWork(self._factory) as uow:
            repo = ModelVersionRepository(uow.session)
            orm = await repo.get(vid)
            assert orm is not None
            orm.artifact_path = str(artifact)

        return TrainDixonColesResult(
            version_id=str(vid),
            artifact_path=str(artifact),
            team_count=len(fit.attack),
            match_count=len(observations),
            home_advantage=fit.home_advantage,
            rho=fit.rho,
        )
