"""Use case: ingest fixtures (matches) from Football-Data.org for a competition+season."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.match import Match, MatchStatus
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.ingestion.adapters.football_data import FootballDataAdapter
from analytis.ingestion.pipeline import IngestionPipeline, IngestionResult
from analytis.persistence.repositories import (
    CompetitionRepository,
    MatchRepository,
    SeasonRepository,
    TeamRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


@dataclass
class FixturesParams:
    competition_external_id: str
    season_label: str


class IngestFixturesUseCase:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        adapter: FootballDataAdapter,
    ) -> None:
        self._factory = session_factory
        self._adapter = adapter
        self._pipeline = IngestionPipeline(session_factory, adapter.source_id)

    async def execute(self, params: FixturesParams) -> IngestionResult:
        async def job(uow: UnitOfWork) -> IngestionResult:
            comps = list(await self._adapter.fetch_competitions())
            matches = list(
                await self._adapter.fetch_matches(
                    params.competition_external_id, params.season_label
                )
            )

            comp = next(
                (c for c in comps if c.external_id == params.competition_external_id),
                None,
            )
            if comp is None:
                raise ValueError(f"competition {params.competition_external_id} not found upstream")

            comp_repo = CompetitionRepository(uow.session)
            season_repo = SeasonRepository(uow.session)
            team_repo = TeamRepository(uow.session)
            match_repo = MatchRepository(uow.session)

            domain_comp = Competition(
                name=comp.name,
                slug=comp.slug,
                competition_type=CompetitionType(comp.competition_type),
                country=comp.country,
                external_ids={comp.source_id: comp.external_id},
            )
            await comp_repo.upsert(domain_comp)
            stored_comp = await comp_repo.get_by_slug(domain_comp.slug)
            assert stored_comp is not None

            season = Season(competition_id=stored_comp.id, label=params.season_label)
            await season_repo.upsert(season)
            stored_season = await season_repo.get(stored_comp.id, params.season_label)
            assert stored_season is not None

            team_type = TeamType(
                "selecao" if domain_comp.competition_type is CompetitionType.SELECAO else "clube"
            )
            team_by_ext: dict[str, Team] = {}
            for m in matches:
                for ext_id, name, short in (
                    (m.home_team_external_id, m.home_team_name, m.home_team_short_name),
                    (m.away_team_external_id, m.away_team_name, m.away_team_short_name),
                ):
                    if ext_id in team_by_ext:
                        continue
                    existing = await team_repo.get_by_external_id(self._adapter.source_id, ext_id)
                    if existing is not None:
                        team_by_ext[ext_id] = existing
                        continue
                    new_team = Team(
                        name=name,
                        short_name=short,
                        team_type=team_type,
                        country=domain_comp.country,
                        external_ids={self._adapter.source_id: ext_id},
                    )
                    await team_repo.upsert(new_team)
                    persisted = await team_repo.get_by_external_id(self._adapter.source_id, ext_id)
                    assert persisted is not None
                    team_by_ext[ext_id] = persisted

            touched = 0
            for m in matches:
                home = team_by_ext[m.home_team_external_id]
                away = team_by_ext[m.away_team_external_id]
                domain_match = Match(
                    season_id=stored_season.id,
                    home_team_id=home.id,
                    away_team_id=away.id,
                    kickoff_utc=m.kickoff_utc,
                    is_home_neutral=m.is_home_neutral,
                    status=MatchStatus(m.status),
                    home_goals=m.home_goals,
                    away_goals=m.away_goals,
                    home_corners=m.home_corners,
                    away_corners=m.away_corners,
                    external_ids={self._adapter.source_id: m.external_id},
                )
                await match_repo.upsert(domain_match)
                touched += 1

            return IngestionResult(records_touched=touched)

        return await self._pipeline.run(
            job_name=f"ingest:fixtures:{params.competition_external_id}:{params.season_label}",
            job=job,
        )
