"""Use case: compute ELO history from finished matches in chronological order."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.domain.elo import EloRating
from analytis.features.elo import DEFAULT_RATING, update_ratings
from analytis.persistence.orm.matches import MatchORM
from analytis.persistence.repositories import EloHistoryRepository
from analytis.persistence.unit_of_work import UnitOfWork


@dataclass
class ComputeEloResult:
    teams_seen: int
    ratings_written: int


class ComputeEloHistoryUseCase:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def execute(
        self, *, reset: bool = True, default_tournament: str = "FIFA World Cup"
    ) -> ComputeEloResult:
        async with UnitOfWork(self._factory) as uow:
            elo_repo = EloHistoryRepository(uow.session)
            if reset:
                await elo_repo.clear_all()

            stmt = (
                select(MatchORM)
                .where(
                    MatchORM.status == "finished",
                    MatchORM.home_goals.is_not(None),
                    MatchORM.away_goals.is_not(None),
                )
                .order_by(MatchORM.kickoff_utc.asc())
            )
            result = await uow.session.scalars(stmt)
            matches = list(result.all())

            current: dict[UUID, float] = {}
            games: dict[UUID, int] = {}

            for m in matches:
                h_rating = current.get(m.home_team_id, DEFAULT_RATING)
                a_rating = current.get(m.away_team_id, DEFAULT_RATING)

                assert m.home_goals is not None
                assert m.away_goals is not None
                new_h, new_a = update_ratings(
                    home_rating=h_rating,
                    away_rating=a_rating,
                    home_goals=m.home_goals,
                    away_goals=m.away_goals,
                    tournament=default_tournament,
                    is_neutral=m.is_home_neutral,
                )
                current[m.home_team_id] = new_h
                current[m.away_team_id] = new_a
                games[m.home_team_id] = games.get(m.home_team_id, 0) + 1
                games[m.away_team_id] = games.get(m.away_team_id, 0) + 1

                await elo_repo.insert(
                    EloRating(
                        id=uuid4(),
                        team_id=m.home_team_id,
                        rating=new_h,
                        as_of=m.kickoff_utc,
                        games_played=games[m.home_team_id],
                    )
                )
                await elo_repo.insert(
                    EloRating(
                        id=uuid4(),
                        team_id=m.away_team_id,
                        rating=new_a,
                        as_of=m.kickoff_utc,
                        games_played=games[m.away_team_id],
                    )
                )

            return ComputeEloResult(teams_seen=len(current), ratings_written=2 * len(matches))
