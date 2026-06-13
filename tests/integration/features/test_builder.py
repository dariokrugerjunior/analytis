"""Integration test for the FeatureBuilder."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.match import Match, MatchStatus
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.features.builder import FeatureBuilder
from analytis.persistence.repositories import (
    CompetitionRepository,
    FeatureSnapshotRepository,
    MatchRepository,
    SeasonRepository,
    TeamRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


async def _seed(session_factory: async_sessionmaker[AsyncSession]) -> Match:
    async with UnitOfWork(session_factory) as uow:
        crepo = CompetitionRepository(uow.session)
        srepo = SeasonRepository(uow.session)
        trepo = TeamRepository(uow.session)
        mrepo = MatchRepository(uow.session)

        comp = Competition(
            name="FIFA World Cup",
            slug="wc-builder-test",
            competition_type=CompetitionType.SELECAO,
            country="INTL",
        )
        await crepo.upsert(comp)
        stored_comp = await crepo.get_by_slug("wc-builder-test")
        assert stored_comp is not None

        season = Season(competition_id=stored_comp.id, label="2026")
        await srepo.upsert(season)
        stored_season = await srepo.get(stored_comp.id, "2026")
        assert stored_season is not None

        for n in ["A-Land", "B-Land", "C-Land"]:
            await trepo.upsert(
                Team(
                    name=n,
                    short_name=n[:5].upper(),
                    team_type=TeamType.SELECAO,
                    country="INT",
                )
            )
        a = await trepo.get_by_name("A-Land")
        b = await trepo.get_by_name("B-Land")
        c = await trepo.get_by_name("C-Land")
        assert a is not None
        assert b is not None
        assert c is not None

        # A vs B history (4 prior matches)
        past = [
            (a.id, c.id, 2, 1, datetime(2024, 6, 1, tzinfo=UTC), "p1"),
            (b.id, c.id, 1, 1, datetime(2024, 6, 5, tzinfo=UTC), "p2"),
            (a.id, b.id, 3, 0, datetime(2024, 10, 10, tzinfo=UTC), "p3"),
            (b.id, a.id, 0, 1, datetime(2025, 3, 15, tzinfo=UTC), "p4"),
        ]
        for h, aw, hg, ag, when, ext in past:
            await mrepo.upsert(
                Match(
                    season_id=stored_season.id,
                    home_team_id=h,
                    away_team_id=aw,
                    kickoff_utc=when,
                    is_home_neutral=False,
                    status=MatchStatus.FINISHED,
                    home_goals=hg,
                    away_goals=ag,
                    external_ids={"test": ext},
                )
            )

        # Upcoming A vs B match (not finished)
        future = Match(
            season_id=stored_season.id,
            home_team_id=a.id,
            away_team_id=b.id,
            kickoff_utc=datetime(2026, 6, 20, tzinfo=UTC),
            is_home_neutral=True,
            status=MatchStatus.SCHEDULED,
            external_ids={"test": "future"},
        )
        await mrepo.upsert(future)
        stored = await mrepo.get_by_external_id("test", "future")
        assert stored is not None
        return stored


@pytest.mark.integration
async def test_builder_produces_expected_keys(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    stored = await _seed(session_factory)

    async with session_factory() as s:
        mrepo = MatchRepository(s)
        builder = FeatureBuilder(mrepo)
        features = await builder.build(stored, as_of=stored.kickoff_utc)

    expected_keys = {
        "home_attack_per_90",
        "home_defense_per_90",
        "away_attack_per_90",
        "away_defense_per_90",
        "home_form_goals_for",
        "home_form_goals_against",
        "home_form_goal_diff",
        "away_form_goals_for",
        "away_form_goals_against",
        "away_form_goal_diff",
        "rest_days_home",
        "rest_days_away",
        "is_home_neutral",
        "h2h_home_win_rate",
        "h2h_total_goals_avg",
        "n_past_home",
        "n_past_away",
        "n_h2h",
    }
    assert set(features.keys()) == expected_keys
    assert features["n_past_home"] >= 1
    assert features["n_h2h"] == 2
    assert features["is_home_neutral"] is True


@pytest.mark.integration
async def test_snapshot_roundtrip(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    stored = await _seed(session_factory)

    async with UnitOfWork(session_factory) as uow:
        mrepo = MatchRepository(uow.session)
        snap_repo = FeatureSnapshotRepository(uow.session)
        builder = FeatureBuilder(mrepo)
        features = await builder.build(stored, as_of=stored.kickoff_utc)
        snap_id = await snap_repo.insert(
            match_id=stored.id,
            snapshot_taken_at=stored.kickoff_utc,
            features=features,
            code_version="test",
        )

    async with session_factory() as s:
        snap_repo2 = FeatureSnapshotRepository(s)
        orm = await snap_repo2.get(snap_id)
        assert orm is not None
        assert orm.code_version == "test"
        assert "home_attack_per_90" in orm.features
