"""Adapter for World Football Elo ratings (CSV/TSV download)."""

import csv
from collections.abc import Iterable
from datetime import date
from io import StringIO

import httpx

from analytis.ingestion.ports import EloRatingDTO
from analytis.ingestion.retry import with_retry


class EloRatingsAdapter:
    source_id = "eloratings"

    def __init__(self, client: httpx.AsyncClient, url: str) -> None:
        self._client = client
        self._url = url

    @with_retry(max_attempts=3, base_delay=1.0)
    async def _download(self) -> str:
        response = await self._client.get(self._url)
        response.raise_for_status()
        return response.text

    async def fetch_world_ratings(self) -> Iterable[EloRatingDTO]:
        raw = await self._download()
        reader = csv.DictReader(StringIO(raw), delimiter="\t")
        result: list[EloRatingDTO] = []
        for row in reader:
            result.append(
                EloRatingDTO(
                    source_id=self.source_id,
                    team_name=row["name"].strip(),
                    country_code=row["country"].strip().upper(),
                    rating=float(row["rating"]),
                    as_of=date.fromisoformat(row["date"].strip()),
                )
            )
        return result
