"""Match repository."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.domain.ids import SeasonId
from analytis.domain.match import Match, MatchStatus
from analytis.persistence.orm.matches import MatchORM
from analytis.persistence.repositories.base import upsert


def _to_domain(orm: MatchORM) -> Match:
    return Match(
        id=orm.id,
        season_id=orm.season_id,
        home_team_id=orm.home_team_id,
        away_team_id=orm.away_team_id,
        kickoff_utc=orm.kickoff_utc,
        venue_id=orm.venue_id,
        referee_id=orm.referee_id,
        is_home_neutral=orm.is_home_neutral,
        status=MatchStatus(orm.status),
        home_goals=orm.home_goals,
        away_goals=orm.away_goals,
        home_corners=orm.home_corners,
        away_corners=orm.away_corners,
        external_ids=dict(orm.external_ids),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class MatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_external_id(self, source: str, ext_id: str) -> Match | None:
        result = await self._session.scalars(
            select(MatchORM).where(MatchORM.external_ids[source].astext == ext_id)
        )
        orm = result.one_or_none()
        return _to_domain(orm) if orm else None

    async def list_by_season(self, season_id: SeasonId) -> list[Match]:
        result = await self._session.scalars(
            select(MatchORM).where(MatchORM.season_id == season_id)
        )
        return [_to_domain(o) for o in result.all()]

    async def list_past_for_team(
        self,
        team_id: UUID,
        as_of: datetime,
        *,
        limit: int = 20,
    ) -> list[Match]:
        """Return up to `limit` finished matches involving `team_id` BEFORE `as_of`,
        ordered most-recent first."""
        result = await self._session.scalars(
            select(MatchORM)
            .where(
                MatchORM.kickoff_utc < as_of,
                MatchORM.status == "finished",
                or_(
                    MatchORM.home_team_id == team_id,
                    MatchORM.away_team_id == team_id,
                ),
            )
            .order_by(MatchORM.kickoff_utc.desc())
            .limit(limit)
        )
        return [_to_domain(o) for o in result.all()]

    async def list_h2h(
        self,
        home_team_id: UUID,
        away_team_id: UUID,
        as_of: datetime,
        *,
        limit: int = 10,
    ) -> list[Match]:
        """Return up to `limit` finished matches between the two teams
        BEFORE `as_of`, ordered most-recent first."""
        result = await self._session.scalars(
            select(MatchORM)
            .where(
                MatchORM.kickoff_utc < as_of,
                MatchORM.status == "finished",
                or_(
                    (MatchORM.home_team_id == home_team_id)
                    & (MatchORM.away_team_id == away_team_id),
                    (MatchORM.home_team_id == away_team_id)
                    & (MatchORM.away_team_id == home_team_id),
                ),
            )
            .order_by(MatchORM.kickoff_utc.desc())
            .limit(limit)
        )
        return [_to_domain(o) for o in result.all()]

    async def upsert(self, match: Match) -> None:
        external_ids = match.external_ids
        if not external_ids:
            raise ValueError("Match must have at least one external_id for upsert")
        source, ext_id = next(iter(external_ids.items()))

        existing = await self.get_by_external_id(source, ext_id)
        target_id = existing.id if existing else match.id

        await upsert(
            self._session,
            MatchORM,
            values={
                "id": target_id,
                "season_id": match.season_id,
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "kickoff_utc": match.kickoff_utc,
                "venue_id": match.venue_id,
                "referee_id": match.referee_id,
                "is_home_neutral": match.is_home_neutral,
                "status": match.status.value,
                "home_goals": match.home_goals,
                "away_goals": match.away_goals,
                "home_corners": match.home_corners,
                "away_corners": match.away_corners,
                "external_ids": external_ids,
            },
            conflict_cols=["id"],
            update_cols=[
                "kickoff_utc",
                "status",
                "home_goals",
                "away_goals",
                "home_corners",
                "away_corners",
                "venue_id",
                "referee_id",
                "external_ids",
            ],
        )
