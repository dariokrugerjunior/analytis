"""Unit tests for the Football-Data.org adapter."""

import httpx
import pytest
import respx

from analytis.ingestion.adapters.football_data import FootballDataAdapter

BASE = "https://api.football-data.org/v4"


@pytest.mark.asyncio
async def test_fetch_competitions() -> None:
    payload = {
        "competitions": [
            {
                "id": 2000,
                "name": "FIFA World Cup",
                "code": "WC",
                "type": "CUP",
                "area": {"code": "INTL", "name": "World"},
            }
        ]
    }
    with respx.mock(base_url=BASE) as mock:
        mock.get("/competitions").respond(200, json=payload)
        async with httpx.AsyncClient(base_url=BASE) as client:
            adapter = FootballDataAdapter(client=client, api_key="x")
            competitions = list(await adapter.fetch_competitions())

    assert len(competitions) == 1
    c = competitions[0]
    assert c.external_id == "2000"
    assert c.slug == "wc"
    assert c.competition_type == "selecao"
    assert c.country == "INTL"


@pytest.mark.asyncio
async def test_fetch_matches_maps_status_and_neutral() -> None:
    payload = {
        "matches": [
            {
                "id": 491189,
                "utcDate": "2026-06-15T22:00:00Z",
                "status": "FINISHED",
                "matchday": 1,
                "stage": "GROUP_STAGE",
                "homeTeam": {"id": 764, "name": "Brazil", "tla": "BRA"},
                "awayTeam": {"id": 763, "name": "Mexico", "tla": "MEX"},
                "score": {
                    "fullTime": {"home": 2, "away": 1},
                    "extraTime": {"home": None, "away": None},
                    "penalties": {"home": None, "away": None},
                },
                "season": {"id": 1, "startDate": "2026-06-11", "endDate": "2026-07-19"},
                "venue": "Estadio Azteca",
                "referees": [{"name": "Joel Aguilar", "role": "REFEREE"}],
            }
        ]
    }
    with respx.mock(base_url=BASE) as mock:
        mock.get("/competitions/2000/matches", params={"season": "2026"}).respond(200, json=payload)
        async with httpx.AsyncClient(base_url=BASE) as client:
            adapter = FootballDataAdapter(client=client, api_key="x")
            matches = list(await adapter.fetch_matches("2000", "2026"))

    assert len(matches) == 1
    m = matches[0]
    assert m.external_id == "491189"
    assert m.home_team_external_id == "764"
    assert m.home_team_name == "Brazil"
    assert m.home_team_short_name == "BRA"
    assert m.away_team_external_id == "763"
    assert m.away_team_name == "Mexico"
    assert m.away_team_short_name == "MEX"
    assert m.away_goals == 1
    assert m.status == "finished"
    assert m.is_home_neutral is True  # World Cup is always neutral
    assert m.referee_name == "Joel Aguilar"
