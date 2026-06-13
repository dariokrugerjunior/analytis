"""Use case: ingest international match history from CSV dataset."""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.match import Match, MatchStatus
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.ingestion.adapters.international_results import (
    InternationalResultsAdapter,
)
from analytis.ingestion.pipeline import IngestionPipeline, IngestionResult
from analytis.persistence.repositories import (
    CompetitionRepository,
    MatchRepository,
    SeasonRepository,
    TeamRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


@dataclass
class InternationalHistoryParams:
    tournaments: set[str] = field(default_factory=lambda: {"FIFA World Cup"})
    min_date: datetime | None = None


_COMPETITION_SLUG = {
    "FIFA World Cup": "fifa-world-cup-history",
    "UEFA Euro": "uefa-euro-history",
    "Copa America": "copa-america-history",
    "African Cup of Nations": "afcon-history",
    "AFC Asian Cup": "afc-asian-cup-history",
}


def _slug_for(tournament: str) -> str:
    return _COMPETITION_SLUG.get(tournament, tournament.lower().replace(" ", "-") + "-history")


class IngestInternationalHistoryUseCase:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        adapter: InternationalResultsAdapter,
    ) -> None:
        self._factory = session_factory
        self._adapter = adapter
        self._pipeline = IngestionPipeline(session_factory, adapter.source_id)

    async def execute(self, params: InternationalHistoryParams) -> IngestionResult:
        async def job(uow: UnitOfWork) -> IngestionResult:
            matches = list(
                await self._adapter.fetch_matches(
                    tournaments=params.tournaments,
                    min_date=params.min_date,
                )
            )

            comp_repo = CompetitionRepository(uow.session)
            season_repo = SeasonRepository(uow.session)
            team_repo = TeamRepository(uow.session)
            match_repo = MatchRepository(uow.session)

            comps_by_tour: dict[str, Competition] = {}
            for tour in {m.tournament for m in matches}:
                domain_comp = Competition(
                    name=tour,
                    slug=_slug_for(tour),
                    competition_type=CompetitionType.SELECAO,
                    country="INTL",
                    external_ids={self._adapter.source_id: tour},
                )
                await comp_repo.upsert(domain_comp)
                stored_comp = await comp_repo.get_by_slug(domain_comp.slug)
                assert stored_comp is not None
                comps_by_tour[tour] = stored_comp

            seasons_by_key: dict[tuple[str, str], Season] = {}
            for m in matches:
                year_label = str(m.kickoff_utc.year)
                key = (m.tournament, year_label)
                if key in seasons_by_key:
                    continue
                season = Season(
                    competition_id=comps_by_tour[m.tournament].id,
                    label=year_label,
                )
                await season_repo.upsert(season)
                stored_season = await season_repo.get(comps_by_tour[m.tournament].id, year_label)
                assert stored_season is not None
                seasons_by_key[key] = stored_season

            team_by_name: dict[str, Team] = {}
            for m in matches:
                for name in (m.home_team_name, m.away_team_name):
                    if name in team_by_name:
                        continue
                    existing = await team_repo.get_by_name(name)
                    if existing is not None:
                        team_by_name[name] = existing
                        continue
                    new_team = Team(
                        name=name,
                        short_name=name[:5].upper(),
                        team_type=TeamType.SELECAO,
                        country="UNK",
                        external_ids={self._adapter.source_id: name},
                    )
                    await team_repo.upsert(new_team)
                    persisted = await team_repo.get_by_name(name)
                    assert persisted is not None
                    team_by_name[name] = persisted

            touched = 0
            for m in matches:
                home = team_by_name[m.home_team_name]
                away = team_by_name[m.away_team_name]
                season = seasons_by_key[(m.tournament, str(m.kickoff_utc.year))]
                domain_match = Match(
                    season_id=season.id,
                    home_team_id=home.id,
                    away_team_id=away.id,
                    kickoff_utc=m.kickoff_utc,
                    is_home_neutral=m.is_neutral,
                    status=MatchStatus.FINISHED,
                    home_goals=m.home_goals,
                    away_goals=m.away_goals,
                    external_ids={self._adapter.source_id: m.external_id},
                )
                await match_repo.upsert(domain_match)
                touched += 1

            return IngestionResult(records_touched=touched)

        return await self._pipeline.run(
            job_name=f"ingest:intl-history:{','.join(sorted(params.tournaments))}",
            job=job,
        )
