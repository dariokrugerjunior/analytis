"""Integration test for FindValueBetsUseCase."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.application.find_value_bets import (
    FindValueBetsParams,
    FindValueBetsUseCase,
)
from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.match import Match, MatchStatus
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.persistence.orm.bets import ValueBetORM
from analytis.persistence.orm.inference import (
    FeatureSnapshotORM,
    ModelVersionORM,
    PredictionORM,
)
from analytis.persistence.repositories import (
    CompetitionRepository,
    MatchRepository,
    OddsRepository,
    SeasonRepository,
    TeamRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


@pytest.mark.integration
async def test_find_value_bets_basic(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with UnitOfWork(session_factory) as uow:
        c = Competition(
            name="VB Cup",
            slug="vb-cup",
            competition_type=CompetitionType.SELECAO,
            country="INTL",
        )
        await CompetitionRepository(uow.session).upsert(c)
        cstored = await CompetitionRepository(uow.session).get_by_slug("vb-cup")
        assert cstored is not None
        s = Season(competition_id=cstored.id, label="2026")
        await SeasonRepository(uow.session).upsert(s)
        sstored = await SeasonRepository(uow.session).get(cstored.id, "2026")
        assert sstored is not None
        for n in ["Team-A", "Team-B"]:
            await TeamRepository(uow.session).upsert(
                Team(
                    name=n,
                    short_name=n[:5].upper(),
                    team_type=TeamType.SELECAO,
                    country="INT",
                )
            )
        a = await TeamRepository(uow.session).get_by_name("Team-A")
        b = await TeamRepository(uow.session).get_by_name("Team-B")
        assert a is not None
        assert b is not None
        match = Match(
            season_id=sstored.id,
            home_team_id=a.id,
            away_team_id=b.id,
            kickoff_utc=datetime(2026, 7, 1, 18, tzinfo=UTC),
            is_home_neutral=True,
            status=MatchStatus.SCHEDULED,
            external_ids={"test": "vb"},
        )
        await MatchRepository(uow.session).upsert(match)
        stored_match = await MatchRepository(uow.session).get_by_external_id("test", "vb")
        assert stored_match is not None

        mv_id = uuid4()
        uow.session.add(
            ModelVersionORM(
                id=mv_id,
                name="vb-mv",
                family="dixon-coles",
                git_sha="sha",
                hyperparams={},
                metrics={},
                is_promoted=False,
            )
        )
        snap_id = uuid4()
        snap_at = datetime(2026, 6, 30, tzinfo=UTC)
        uow.session.add(
            FeatureSnapshotORM(
                id=snap_id,
                match_id=stored_match.id,
                snapshot_taken_at=snap_at,
                features={},
                created_at=snap_at,
            )
        )
        await uow.session.flush()
        uow.session.add(
            PredictionORM(
                id=uuid4(),
                match_id=stored_match.id,
                market="1x2",
                outcome="home",
                prob=0.55,
                ci_low=0.50,
                ci_high=0.60,
                model_version_id=mv_id,
                feature_snapshot_id=snap_id,
                created_at=snap_at,
            )
        )
        await OddsRepository(uow.session).insert_quote(
            match_id=stored_match.id,
            bookmaker="pinnacle",
            market="1x2",
            outcome="home",
            decimal_odds=2.10,
            snapshot_taken_at=snap_at,
        )

    use_case = FindValueBetsUseCase(session_factory)
    result = await use_case.execute(
        FindValueBetsParams(
            match_id=stored_match.id,
            model_version_id=mv_id,
            min_edge=0.01,
            bankroll=1000.0,
            kelly_fraction_value=0.25,
        )
    )
    assert result.bets_found == 1

    async with session_factory() as verify_session:
        bets = (
            await verify_session.scalars(
                select(ValueBetORM).where(ValueBetORM.match_id == stored_match.id)
            )
        ).all()
        assert len(bets) == 1
        bet = bets[0]
        assert bet.outcome == "home"
        assert bet.decimal_odds == pytest.approx(2.10)
        assert bet.suggested_stake_units > 0
