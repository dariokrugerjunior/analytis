"""Integration test for the Dixon-Coles training use case."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.application.train_dixon_coles import (
    TrainDixonColesParams,
    TrainDixonColesUseCase,
)
from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.match import Match, MatchStatus
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.persistence.orm.inference import ModelVersionORM
from analytis.persistence.repositories import (
    CompetitionRepository,
    MatchRepository,
    SeasonRepository,
    TeamRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


async def _seed_history(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with UnitOfWork(session_factory) as uow:
        crepo = CompetitionRepository(uow.session)
        srepo = SeasonRepository(uow.session)
        trepo = TeamRepository(uow.session)
        mrepo = MatchRepository(uow.session)

        comp = Competition(
            name="Train Test League",
            slug="train-test",
            competition_type=CompetitionType.SELECAO,
            country="INTL",
        )
        await crepo.upsert(comp)
        stored_comp = await crepo.get_by_slug("train-test")
        assert stored_comp is not None

        season = Season(competition_id=stored_comp.id, label="2024")
        await srepo.upsert(season)
        stored_season = await srepo.get(stored_comp.id, "2024")
        assert stored_season is not None

        for n in ["Alpha", "Beta", "Gamma", "Delta"]:
            await trepo.upsert(
                Team(
                    name=n,
                    short_name=n[:5].upper(),
                    team_type=TeamType.SELECAO,
                    country="INT",
                )
            )
        teams = {}
        for n in ["Alpha", "Beta", "Gamma", "Delta"]:
            t = await trepo.get_by_name(n)
            assert t is not None
            teams[n] = t

        start = datetime(2024, 1, 1, tzinfo=UTC)
        names = ["Alpha", "Beta", "Gamma", "Delta"]
        day = 0
        ext_idx = 0
        for round_idx in range(4):
            for i, h in enumerate(names):
                for j, a in enumerate(names):
                    if i == j:
                        continue
                    when = start + timedelta(days=day)
                    day += 1
                    await mrepo.upsert(
                        Match(
                            season_id=stored_season.id,
                            home_team_id=teams[h].id,
                            away_team_id=teams[a].id,
                            kickoff_utc=when,
                            is_home_neutral=False,
                            status=MatchStatus.FINISHED,
                            home_goals=(i + round_idx) % 4,
                            away_goals=(j + round_idx + 1) % 4,
                            external_ids={"test": f"t{ext_idx}"},
                        )
                    )
                    ext_idx += 1


@pytest.mark.integration
async def test_train_dixon_coles_end_to_end(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    await _seed_history(session_factory)

    use_case = TrainDixonColesUseCase(session_factory, models_dir=tmp_path)
    result = await use_case.execute(
        TrainDixonColesParams(
            since=datetime(2023, 1, 1, tzinfo=UTC),
            max_iter=100,
            decay_per_day=0.0,
            name="dc-test-run",
        )
    )
    assert result.team_count == 4
    assert result.match_count >= 12
    artifact = Path(result.artifact_path)
    assert artifact.exists()
    assert artifact.suffix == ".pkl"

    async with session_factory() as s:
        n_versions = await s.scalar(select(func.count()).select_from(ModelVersionORM))
        assert n_versions == 1
        orm = (
            await s.scalars(select(ModelVersionORM).where(ModelVersionORM.name == "dc-test-run"))
        ).one()
        assert orm.family == "dixon-coles"
        assert orm.hyperparams["decay_per_day"] == 0.0
        assert orm.metrics.get("n_matches", 0) >= 12
