"""Integration test for the fixtures ingestion use case end-to-end."""

from collections.abc import Iterable

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.application.ingest_fixtures import (
    FixturesParams,
    IngestFixturesUseCase,
)
from analytis.ingestion.adapters.football_data import FootballDataAdapter
from analytis.ingestion.ports import CompetitionDTO, MatchDTO
from analytis.persistence.orm.ingestion import IngestionRunORM
from analytis.persistence.orm.matches import MatchORM


class _FakeAdapter:
    source_id = "footballdata"

    def __init__(
        self,
        competitions: list[CompetitionDTO],
        matches: list[MatchDTO],
    ) -> None:
        self._competitions = competitions
        self._matches = matches

    async def fetch_competitions(self) -> Iterable[CompetitionDTO]:
        return list(self._competitions)

    async def fetch_matches(
        self, _competition_external_id: str, _season_label: str
    ) -> Iterable[MatchDTO]:
        return list(self._matches)


@pytest.mark.integration
async def test_ingest_fixtures_end_to_end(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from datetime import UTC, datetime

    comp = CompetitionDTO(
        source_id="footballdata",
        external_id="2000",
        name="FIFA World Cup",
        slug="wc",
        competition_type="selecao",
        country="INTL",
    )
    matches = [
        MatchDTO(
            source_id="footballdata",
            external_id="491189",
            competition_external_id="2000",
            season_label="2026",
            home_team_external_id="764",
            home_team_name="Brazil",
            home_team_short_name="BRA",
            away_team_external_id="763",
            away_team_name="Mexico",
            away_team_short_name="MEX",
            kickoff_utc=datetime(2026, 6, 15, 22, 0, tzinfo=UTC),
            is_home_neutral=True,
            status="finished",
            stage="GROUP_STAGE",
            home_goals=2,
            away_goals=1,
            home_corners=None,
            away_corners=None,
            venue_name="Estadio Azteca",
            referee_name="Joel Aguilar",
        ),
    ]

    use_case = IngestFixturesUseCase(
        session_factory,
        adapter=_FakeAdapter(competitions=[comp], matches=matches),  # type: ignore[arg-type]
    )

    result = await use_case.execute(FixturesParams("2000", "2026"))
    assert result.records_touched == 1

    async with session_factory() as s:
        match_count = await s.scalar(select(func.count()).select_from(MatchORM))
        run_count = await s.scalar(
            select(func.count())
            .select_from(IngestionRunORM)
            .where(IngestionRunORM.status == "succeeded")
        )
        assert match_count == 1
        assert run_count == 1

    # Idempotency: rerun, no new rows
    result2 = await use_case.execute(FixturesParams("2000", "2026"))
    assert result2.records_touched == 1
    async with session_factory() as s:
        match_count2 = await s.scalar(select(func.count()).select_from(MatchORM))
        assert match_count2 == 1


# Touch FootballDataAdapter so mypy keeps it imported for type guards
_assert_adapter_is_protocol_compatible: type = FootballDataAdapter
