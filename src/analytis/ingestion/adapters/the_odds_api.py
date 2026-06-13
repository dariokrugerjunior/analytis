"""Adapter for The Odds API (https://the-odds-api.com).

Free tier: ~500 requests/month. We hit the /odds endpoint per sport_key.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from analytis.ingestion.retry import with_retry


@dataclass(frozen=True)
class TheOddsOutcome:
    name: str
    decimal_odds: float


@dataclass(frozen=True)
class TheOddsMarket:
    market_key: str
    outcomes: list[TheOddsOutcome]


@dataclass(frozen=True)
class TheOddsBookmaker:
    key: str
    title: str
    last_update: datetime
    markets: list[TheOddsMarket]


@dataclass(frozen=True)
class TheOddsEvent:
    external_id: str
    sport_key: str
    commence_time: datetime
    home_team: str
    away_team: str
    bookmakers: list[TheOddsBookmaker]


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class TheOddsApiAdapter:
    source_id = "the_odds_api"

    def __init__(self, client: httpx.AsyncClient, api_key: str) -> None:
        self._client = client
        self._api_key = api_key

    @with_retry(max_attempts=3, base_delay=1.0)
    async def _get(self, path: str, **params: Any) -> Any:
        response = await self._client.get(
            path,
            params={"apiKey": self._api_key, **params},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    async def fetch_odds(
        self,
        *,
        sport_key: str = "soccer_fifa_world_cup",
        markets: tuple[str, ...] = ("h2h", "totals", "btts"),
        regions: str = "eu,us,uk",
    ) -> Iterable[TheOddsEvent]:
        data = await self._get(
            f"/sports/{sport_key}/odds",
            regions=regions,
            markets=",".join(markets),
            oddsFormat="decimal",
        )
        events: list[TheOddsEvent] = []
        for ev in data:
            bookmakers: list[TheOddsBookmaker] = []
            for bm in ev.get("bookmakers", []):
                ms: list[TheOddsMarket] = []
                for m in bm.get("markets", []):
                    outs = [
                        TheOddsOutcome(name=o["name"], decimal_odds=float(o["price"]))
                        for o in m.get("outcomes", [])
                    ]
                    ms.append(TheOddsMarket(market_key=m["key"], outcomes=outs))
                bookmakers.append(
                    TheOddsBookmaker(
                        key=bm["key"],
                        title=bm["title"],
                        last_update=_parse_iso(bm["last_update"]),
                        markets=ms,
                    )
                )
            events.append(
                TheOddsEvent(
                    external_id=ev["id"],
                    sport_key=ev["sport_key"],
                    commence_time=_parse_iso(ev["commence_time"]),
                    home_team=ev["home_team"],
                    away_team=ev["away_team"],
                    bookmakers=bookmakers,
                )
            )
        return events
