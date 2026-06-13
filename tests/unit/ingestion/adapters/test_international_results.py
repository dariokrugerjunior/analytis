"""Unit tests for the International Results CSV adapter."""

from datetime import UTC, datetime

import httpx
import pytest
import respx

from analytis.ingestion.adapters.international_results import (
    InternationalResultsAdapter,
)

URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"

CSV_FIXTURE = (
    "date,home_team,away_team,home_score,away_score,tournament,city,country,neutral\n"
    "2018-06-14,Russia,Saudi Arabia,5,0,FIFA World Cup,Moscow,Russia,False\n"
    "2018-06-15,Egypt,Uruguay,0,1,FIFA World Cup,Yekaterinburg,Russia,True\n"
    "2022-11-20,Qatar,Ecuador,0,2,FIFA World Cup,Al Khor,Qatar,False\n"
)


@pytest.mark.asyncio
async def test_fetch_matches_parses_csv() -> None:
    with respx.mock() as mock:
        mock.get(URL).respond(200, text=CSV_FIXTURE)
        async with httpx.AsyncClient() as client:
            adapter = InternationalResultsAdapter(client=client, url=URL)
            matches = list(await adapter.fetch_matches())

    assert len(matches) == 3
    m0 = matches[0]
    assert m0.home_team_name == "Russia"
    assert m0.away_team_name == "Saudi Arabia"
    assert m0.home_goals == 5
    assert m0.away_goals == 0
    assert m0.kickoff_utc == datetime(2018, 6, 14, 12, 0, tzinfo=UTC)
    assert m0.tournament == "FIFA World Cup"
    assert m0.is_neutral is False
    assert matches[1].is_neutral is True


@pytest.mark.asyncio
async def test_fetch_matches_filters_by_tournament() -> None:
    with respx.mock() as mock:
        mock.get(URL).respond(200, text=CSV_FIXTURE)
        async with httpx.AsyncClient() as client:
            adapter = InternationalResultsAdapter(client=client, url=URL)
            wc = list(await adapter.fetch_matches(tournaments={"FIFA World Cup"}))

    assert len(wc) == 3


@pytest.mark.asyncio
async def test_fetch_matches_filters_by_date() -> None:
    with respx.mock() as mock:
        mock.get(URL).respond(200, text=CSV_FIXTURE)
        async with httpx.AsyncClient() as client:
            adapter = InternationalResultsAdapter(client=client, url=URL)
            recent = list(await adapter.fetch_matches(min_date=datetime(2022, 1, 1, tzinfo=UTC)))

    assert len(recent) == 1
    assert recent[0].home_team_name == "Qatar"
