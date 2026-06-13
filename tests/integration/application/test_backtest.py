"""Integration test for the BacktestUseCase."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.application.backtest import (
    BacktestParams,
    BacktestUseCase,
)
from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.match import Match, MatchStatus
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.persistence.repositories import (
    CompetitionRepository,
    MatchRepository,
    SeasonRepository,
    TeamRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


async def _seed_long_history(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with UnitOfWork(session_factory) as uow:
        crepo = CompetitionRepository(uow.session)
        srepo = SeasonRepository(uow.session)
        trepo = TeamRepository(uow.session)
        mrepo = MatchRepository(uow.session)

        comp = Competition(
            name="Backtest Cup",
            slug="backtest-cup",
            competition_type=CompetitionType.SELECAO,
            country="INTL",
        )
        await crepo.upsert(comp)
        stored_comp = await crepo.get_by_slug("backtest-cup")
        assert stored_comp is not None

        season = Season(competition_id=stored_comp.id, label="2024")
        await srepo.upsert(season)
        stored_season = await srepo.get(stored_comp.id, "2024")
        assert stored_season is not None

        names = ["A", "B", "C", "D", "E", "F"]
        for n in names:
            await trepo.upsert(
                Team(
                    name=n,
                    short_name=n,
                    team_type=TeamType.SELECAO,
                    country="INT",
                )
            )
        teams = {}
        for n in names:
            t = await trepo.get_by_name(n)
            assert t is not None
            teams[n] = t

        start = datetime(2024, 1, 1, tzinfo=UTC)
        day = 0
        ext = 0
        for _round in range(8):
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
                            home_goals=(i + j + ext) % 4,
                            away_goals=(j + ext) % 3,
                            external_ids={"test": f"bt{ext}"},
                        )
                    )
                    ext += 1


@pytest.mark.integration
async def test_backtest_end_to_end(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    await _seed_long_history(session_factory)

    use_case = BacktestUseCase(session_factory, reports_dir=tmp_path)
    result = await use_case.execute(
        BacktestParams(
            since=datetime(2023, 1, 1, tzinfo=UTC),
            until=datetime(2026, 1, 1, tzinfo=UTC),
            min_train_size=60,
            test_size=30,
            max_iter=100,
            decay_per_day=0.0,
        )
    )
    assert result.n_slices >= 1
    assert result.total_test_matches >= 30
    assert "brier_1x2_home" in result.metrics
    assert 0.0 <= result.metrics["brier_1x2_home"] <= 1.0

    report_path = Path(result.report_path)
    assert report_path.exists()
    report = json.loads(report_path.read_text())
    assert "slices" in report
    assert len(report["slices"]) == result.n_slices
