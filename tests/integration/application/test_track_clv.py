"""Integration test for CLV tracking."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.application.track_clv import TrackCLVParams, TrackCLVUseCase
from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.match import Match, MatchStatus
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.persistence.orm.bets import ValueBetORM
from analytis.persistence.orm.inference import ModelVersionORM
from analytis.persistence.repositories import (
    CompetitionRepository,
    MatchRepository,
    OddsRepository,
    SeasonRepository,
    TeamRepository,
    ValueBetRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


@pytest.mark.integration
async def test_track_clv_updates_bet(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with UnitOfWork(session_factory) as uow:
        c = Competition(
            name="CLV Cup",
            slug="clv-cup",
            competition_type=CompetitionType.SELECAO,
            country="INTL",
        )
        await CompetitionRepository(uow.session).upsert(c)
        cstored = await CompetitionRepository(uow.session).get_by_slug("clv-cup")
        assert cstored is not None
        s = Season(competition_id=cstored.id, label="2026")
        await SeasonRepository(uow.session).upsert(s)
        sstored = await SeasonRepository(uow.session).get(cstored.id, "2026")
        assert sstored is not None
        for n in ["X", "Y"]:
            await TeamRepository(uow.session).upsert(
                Team(
                    name=n,
                    short_name=n,
                    team_type=TeamType.SELECAO,
                    country="INT",
                )
            )
        x = await TeamRepository(uow.session).get_by_name("X")
        y = await TeamRepository(uow.session).get_by_name("Y")
        assert x is not None
        assert y is not None
        match = Match(
            season_id=sstored.id,
            home_team_id=x.id,
            away_team_id=y.id,
            kickoff_utc=datetime(2026, 7, 1, 18, tzinfo=UTC),
            is_home_neutral=True,
            status=MatchStatus.SCHEDULED,
            external_ids={"test": "clv"},
        )
        await MatchRepository(uow.session).upsert(match)
        stored_match = await MatchRepository(uow.session).get_by_external_id("test", "clv")
        assert stored_match is not None

        mv_id = uuid4()
        uow.session.add(
            ModelVersionORM(
                id=mv_id,
                name="clv-mv",
                family="dixon-coles",
                git_sha="sha",
                hyperparams={},
                metrics={},
                is_promoted=False,
            )
        )
        await uow.session.flush()
        # 1. Insert a value bet (we took 2.50 on home)
        bet_id = await ValueBetRepository(uow.session).insert(
            match_id=stored_match.id,
            model_version_id=mv_id,
            market="1x2",
            outcome="home",
            bookmaker="pinnacle",
            our_prob=0.50,
            market_prob=0.40,
            decimal_odds=2.50,
            edge=0.05,
            kelly_fraction=0.05,
            suggested_stake_units=10.0,
            found_at=datetime(2026, 6, 25, tzinfo=UTC),
        )
        # 2. Insert closing odds (closer to kickoff): 2.20 (line moved with us)
        await OddsRepository(uow.session).insert_quote(
            match_id=stored_match.id,
            bookmaker="pinnacle",
            market="1x2",
            outcome="home",
            decimal_odds=2.20,
            snapshot_taken_at=datetime(2026, 7, 1, 17, 45, tzinfo=UTC),
        )

    use_case = TrackCLVUseCase(session_factory)
    result = await use_case.execute(TrackCLVParams(match_id=stored_match.id))
    assert result.bets_updated == 1

    async with session_factory() as verify_session:
        bet = (
            await verify_session.scalars(select(ValueBetORM).where(ValueBetORM.id == bet_id))
        ).one()
        assert bet.closing_decimal_odds == pytest.approx(2.20)
        assert bet.closing_clv is not None
        assert bet.closing_clv > 0
