"""Unit tests for The Odds API adapter."""

from datetime import UTC, datetime

import httpx
import pytest
import respx

from analytis.ingestion.adapters.the_odds_api import TheOddsApiAdapter

BASE = "https://api.the-odds-api.com/v4"


@pytest.mark.asyncio
async def test_fetch_odds_h2h_only() -> None:
    payload = [
        {
            "id": "ev1",
            "sport_key": "soccer_fifa_world_cup",
            "commence_time": "2026-06-13T22:00:00Z",
            "home_team": "Brazil",
            "away_team": "Morocco",
            "bookmakers": [
                {
                    "key": "pinnacle",
                    "title": "Pinnacle",
                    "last_update": "2026-06-13T15:00:00Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Brazil", "price": 2.40},
                                {"name": "Draw", "price": 3.10},
                                {"name": "Morocco", "price": 3.20},
                            ],
                        }
                    ],
                }
            ],
        }
    ]

    with respx.mock(base_url=BASE) as mock:
        mock.get("/sports/soccer_fifa_world_cup/odds").respond(200, json=payload)
        async with httpx.AsyncClient(base_url=BASE) as client:
            adapter = TheOddsApiAdapter(client=client, api_key="x")
            events = list(
                await adapter.fetch_odds(
                    sport_key="soccer_fifa_world_cup",
                    markets=("h2h",),
                )
            )

    assert len(events) == 1
    ev = events[0]
    assert ev.home_team == "Brazil"
    assert ev.away_team == "Morocco"
    assert ev.commence_time == datetime(2026, 6, 13, 22, 0, tzinfo=UTC)
    assert len(ev.bookmakers) == 1
    bm = ev.bookmakers[0]
    assert bm.key == "pinnacle"
    home_market = next(m for m in bm.markets if m.market_key == "h2h")
    home_outcome = next(o for o in home_market.outcomes if o.name == "Brazil")
    assert home_outcome.decimal_odds == 2.40
