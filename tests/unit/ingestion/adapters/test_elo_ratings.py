"""Unit tests for the ELO ratings adapter."""

from datetime import date

import httpx
import pytest
import respx

from analytis.ingestion.adapters.elo_ratings import EloRatingsAdapter

URL = "http://www.eloratings.net/World.tsv"

# Minimal TSV mock — columns: rank, name, country, rating, date
TSV_FIXTURE = (
    "rank\tname\tcountry\trating\tdate\n"
    "1\tBrazil\tBRA\t2150.0\t2026-06-12\n"
    "2\tArgentina\tARG\t2120.0\t2026-06-12\n"
)


@pytest.mark.asyncio
async def test_fetch_world_ratings_parses_tsv() -> None:
    with respx.mock() as mock:
        mock.get(URL).respond(200, text=TSV_FIXTURE)
        async with httpx.AsyncClient() as client:
            adapter = EloRatingsAdapter(client=client, url=URL)
            ratings = list(await adapter.fetch_world_ratings())

    assert len(ratings) == 2
    bra = ratings[0]
    assert bra.team_name == "Brazil"
    assert bra.country_code == "BRA"
    assert bra.rating == 2150.0
    assert bra.as_of == date(2026, 6, 12)
