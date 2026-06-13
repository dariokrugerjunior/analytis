"""Integration test for odds ingestion."""

from collections.abc import Iterable
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.application.ingest_odds import IngestOddsParams, IngestOddsUseCase
from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.match import Match, MatchStatus
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.ingestion.adapters.the_odds_api import (
    TheOddsBookmaker,
    TheOddsEvent,
    TheOddsMarket,
    TheOddsOutcome,
)
from analytis.persistence.orm.odds import OddsSnapshotORM
from analytis.persistence.repositories import (
    CompetitionRepository,
    MatchRepository,
    SeasonRepository,
    TeamRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


class _FakeAdapter:
    source_id = "the_odds_api"

    def __init__(self, events: list[TheOddsEvent]) -> None:
        self._events = events

    async def fetch_odds(self, **_: object) -> Iterable[TheOddsEvent]:
        return list(self._events)


async def _seed_match(
    factory: async_sessionmaker[AsyncSession],
) -> Match:
    async with UnitOfWork(factory) as uow:
        c = Competition(
            name="Odds Test Cup",
            slug="odds-test",
            competition_type=CompetitionType.SELECAO,
            country="INTL",
        )
        await CompetitionRepository(uow.session).upsert(c)
        cstored = await CompetitionRepository(uow.session).get_by_slug("odds-test")
        assert cstored is not None
        s = Season(competition_id=cstored.id, label="2026")
        await SeasonRepository(uow.session).upsert(s)
        sstored = await SeasonRepository(uow.session).get(cstored.id, "2026")
        assert sstored is not None
        for n in ["Brazil", "Morocco"]:
            await TeamRepository(uow.session).upsert(
                Team(
                    name=n,
                    short_name=n[:5].upper(),
                    team_type=TeamType.SELECAO,
                    country="INT",
                )
            )
        bra = await TeamRepository(uow.session).get_by_name("Brazil")
        mar = await TeamRepository(uow.session).get_by_name("Morocco")
        assert bra is not None
        assert mar is not None
        m = Match(
            season_id=sstored.id,
            home_team_id=bra.id,
            away_team_id=mar.id,
            kickoff_utc=datetime(2026, 6, 13, 22, 0, tzinfo=UTC),
            is_home_neutral=True,
            status=MatchStatus.SCHEDULED,
            external_ids={"test": "odds-target"},
        )
        await MatchRepository(uow.session).upsert(m)
        stored = await MatchRepository(uow.session).get_by_external_id("test", "odds-target")
        assert stored is not None
        return stored


@pytest.mark.integration
async def test_ingest_odds_h2h_only(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed_match(session_factory)
    event = TheOddsEvent(
        external_id="ev1",
        sport_key="soccer_fifa_world_cup",
        commence_time=datetime(2026, 6, 13, 22, 0, tzinfo=UTC),
        home_team="Brazil",
        away_team="Morocco",
        bookmakers=[
            TheOddsBookmaker(
                key="pinnacle",
                title="Pinnacle",
                last_update=datetime(2026, 6, 13, 15, 0, tzinfo=UTC),
                markets=[
                    TheOddsMarket(
                        market_key="h2h",
                        outcomes=[
                            TheOddsOutcome(name="Brazil", decimal_odds=2.40),
                            TheOddsOutcome(name="Draw", decimal_odds=3.10),
                            TheOddsOutcome(name="Morocco", decimal_odds=3.20),
                        ],
                    )
                ],
            )
        ],
    )
    adapter = _FakeAdapter([event])
    use_case = IngestOddsUseCase(session_factory, adapter)  # type: ignore[arg-type]
    result = await use_case.execute(IngestOddsParams())
    assert result.records_touched == 3

    async with session_factory() as s:
        n = await s.scalar(select(func.count()).select_from(OddsSnapshotORM))
        assert n == 3

    # Rerun is idempotent
    result2 = await use_case.execute(IngestOddsParams())
    assert result2.records_touched == 0
    async with session_factory() as s:
        n2 = await s.scalar(select(func.count()).select_from(OddsSnapshotORM))
        assert n2 == 3
