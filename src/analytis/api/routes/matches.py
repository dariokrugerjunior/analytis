"""Routes for matches listings."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.api.deps import require_api_key
from analytis.config import Settings, get_settings
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.orm.matches import MatchORM

router = APIRouter(prefix="/matches", tags=["matches"])


@asynccontextmanager
async def _session(settings: Settings) -> AsyncIterator[AsyncSession]:
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


class MatchItem(BaseModel):
    id: UUID
    home_team: str
    away_team: str
    kickoff_utc: datetime
    status: str
    home_goals: int | None
    away_goals: int | None
    is_home_neutral: bool


class MatchesList(BaseModel):
    items: list[MatchItem]


@router.get(
    "",
    response_model=MatchesList,
    dependencies=[Depends(require_api_key)],
)
async def list_matches(
    upcoming: bool = Query(False),
    days: int = Query(7, ge=1, le=30),
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> MatchesList:
    async with _session(settings) as session:
        team_rows = (await session.execute(select(TeamORM.id, TeamORM.name))).all()
        id_to_name: dict[UUID, str] = {row.id: row.name for row in team_rows}

        stmt = select(MatchORM)
        if upcoming:
            now = datetime.now(UTC)
            stmt = stmt.where(
                MatchORM.kickoff_utc >= now,
                MatchORM.kickoff_utc < now + timedelta(days=days),
                MatchORM.status.in_(("scheduled", "live")),
            )
        stmt = stmt.order_by(MatchORM.kickoff_utc.asc()).limit(200)

        rows = list((await session.scalars(stmt)).all())
        items = [
            MatchItem(
                id=m.id,
                home_team=id_to_name.get(m.home_team_id, "?"),
                away_team=id_to_name.get(m.away_team_id, "?"),
                kickoff_utc=m.kickoff_utc,
                status=m.status,
                home_goals=m.home_goals,
                away_goals=m.away_goals,
                is_home_neutral=m.is_home_neutral,
            )
            for m in rows
        ]
        return MatchesList(items=items)
