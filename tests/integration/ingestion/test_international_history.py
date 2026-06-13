"""Integration test for international history ingestion."""

from collections.abc import Iterable
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.application.ingest_international_history import (
    IngestInternationalHistoryUseCase,
    InternationalHistoryParams,
)
from analytis.ingestion.adapters.international_results import (
    InternationalMatchDTO,
)
from analytis.persistence.orm.matches import MatchORM


class _FakeAdapter:
    source_id = "intl_results"

    def __init__(self, matches: list[InternationalMatchDTO]) -> None:
        self._matches = matches

    async def fetch_matches(
        self,
        tournaments: set[str] | None = None,
        min_date: datetime | None = None,
    ) -> Iterable[InternationalMatchDTO]:
        return list(self._matches)


@pytest.mark.integration
async def test_ingest_history_end_to_end(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    matches = [
        InternationalMatchDTO(
            source_id="intl_results",
            external_id="2018-06-14_Russia_Saudi_Arabia",
            home_team_name="Russia",
            away_team_name="Saudi Arabia",
            home_goals=5,
            away_goals=0,
            kickoff_utc=datetime(2018, 6, 14, 12, 0, tzinfo=UTC),
            tournament="FIFA World Cup",
            city="Moscow",
            host_country="Russia",
            is_neutral=False,
        ),
        InternationalMatchDTO(
            source_id="intl_results",
            external_id="2022-11-20_Qatar_Ecuador",
            home_team_name="Qatar",
            away_team_name="Ecuador",
            home_goals=0,
            away_goals=2,
            kickoff_utc=datetime(2022, 11, 20, 12, 0, tzinfo=UTC),
            tournament="FIFA World Cup",
            city="Al Khor",
            host_country="Qatar",
            is_neutral=False,
        ),
    ]

    use_case = IngestInternationalHistoryUseCase(
        session_factory,
        adapter=_FakeAdapter(matches),  # type: ignore[arg-type]
    )

    result = await use_case.execute(InternationalHistoryParams(tournaments={"FIFA World Cup"}))
    assert result.records_touched == 2

    async with session_factory() as s:
        match_count = await s.scalar(select(func.count()).select_from(MatchORM))
        assert match_count == 2

    # Idempotency
    result2 = await use_case.execute(InternationalHistoryParams(tournaments={"FIFA World Cup"}))
    assert result2.records_touched == 2
    async with session_factory() as s:
        match_count2 = await s.scalar(select(func.count()).select_from(MatchORM))
        assert match_count2 == 2
