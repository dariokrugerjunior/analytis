"""Use case: ingest odds from The Odds API into our DB."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.ingestion.adapters.the_odds_api import TheOddsApiAdapter
from analytis.ingestion.pipeline import IngestionPipeline, IngestionResult
from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.orm.matches import MatchORM
from analytis.persistence.repositories import OddsRepository
from analytis.persistence.unit_of_work import UnitOfWork

_MARKET_KEY_MAP = {
    "h2h": "1x2",
    "totals": "over_under_goals",
    "btts": "btts",
}


def _outcome_for_h2h(name: str, home: str, away: str) -> str | None:
    n = name.strip().lower()
    if n == home.lower():
        return "home"
    if n == away.lower():
        return "away"
    if n == "draw":
        return "draw"
    return None


def _outcome_for_totals(name: str) -> str | None:
    n = name.strip().lower()
    # The Odds API uses outcomes like "Over" / "Under" with point info as a
    # separate "point" key per outcome. Without point info we default to 2.5.
    if n.startswith("over"):
        return "over_2.5"
    if n.startswith("under"):
        return "under_2.5"
    return None


@dataclass(frozen=True)
class IngestOddsParams:
    sport_key: str = "soccer_fifa_world_cup"


class IngestOddsUseCase:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        adapter: TheOddsApiAdapter,
    ) -> None:
        self._factory = session_factory
        self._adapter = adapter
        self._pipeline = IngestionPipeline(session_factory, adapter.source_id)

    async def execute(self, params: IngestOddsParams) -> IngestionResult:
        async def job(uow: UnitOfWork) -> IngestionResult:
            events = list(await self._adapter.fetch_odds(sport_key=params.sport_key))
            odds_repo = OddsRepository(uow.session)

            team_rows = (await uow.session.execute(select(TeamORM.id, TeamORM.name))).all()
            name_to_id = {r.name.lower(): r.id for r in team_rows}

            match_rows = (
                (
                    await uow.session.execute(
                        select(MatchORM).where(MatchORM.status.in_(("scheduled", "live")))
                    )
                )
                .scalars()
                .all()
            )

            inserted = 0
            for ev in events:
                home_id = name_to_id.get(ev.home_team.lower())
                away_id = name_to_id.get(ev.away_team.lower())
                if home_id is None or away_id is None:
                    continue
                match = next(
                    (
                        m
                        for m in match_rows
                        if m.home_team_id == home_id and m.away_team_id == away_id
                    ),
                    None,
                )
                if match is None:
                    continue
                for bm in ev.bookmakers:
                    for m in bm.markets:
                        canonical_market = _MARKET_KEY_MAP.get(m.market_key)
                        if canonical_market is None:
                            continue
                        for o in m.outcomes:
                            if canonical_market == "1x2":
                                outcome = _outcome_for_h2h(o.name, ev.home_team, ev.away_team)
                            elif canonical_market == "over_under_goals":
                                outcome = _outcome_for_totals(o.name)
                            elif canonical_market == "btts":
                                outcome = "yes" if o.name.strip().lower() == "yes" else "no"
                            else:
                                outcome = None
                            if outcome is None:
                                continue
                            ok = await odds_repo.insert_quote(
                                match_id=match.id,
                                bookmaker=bm.key,
                                market=canonical_market,
                                outcome=outcome,
                                decimal_odds=o.decimal_odds,
                                snapshot_taken_at=bm.last_update,
                            )
                            if ok:
                                inserted += 1
            return IngestionResult(records_touched=inserted)

        return await self._pipeline.run(
            job_name=f"ingest:odds:{params.sport_key}",
            job=job,
        )
