"""Adapter for martj42/international_results CSV dataset.

Source: https://github.com/martj42/international_results
License: CC0 (public domain). Contains every international football match
played since 1872 - ~45,000 rows, updated regularly.
"""

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from io import StringIO

import httpx

from analytis.ingestion.retry import with_retry


@dataclass(frozen=True)
class InternationalMatchDTO:
    source_id: str
    external_id: str  # synthetic: "{date}_{home}_{away}"
    home_team_name: str
    away_team_name: str
    home_goals: int
    away_goals: int
    kickoff_utc: datetime
    tournament: str
    city: str | None
    host_country: str | None
    is_neutral: bool


class InternationalResultsAdapter:
    source_id = "intl_results"
    DEFAULT_URL = (
        "https://raw.githubusercontent.com/" "martj42/international_results/master/results.csv"
    )

    def __init__(self, client: httpx.AsyncClient, url: str | None = None) -> None:
        self._client = client
        self._url = url or self.DEFAULT_URL

    @with_retry(max_attempts=3, base_delay=1.0)
    async def _download(self) -> str:
        response = await self._client.get(self._url, timeout=60.0)
        response.raise_for_status()
        return response.text

    async def fetch_matches(
        self,
        tournaments: set[str] | None = None,
        min_date: datetime | None = None,
    ) -> Iterable[InternationalMatchDTO]:
        raw = await self._download()
        reader = csv.DictReader(StringIO(raw))
        result: list[InternationalMatchDTO] = []
        for row in reader:
            tour = row["tournament"].strip()
            if tournaments is not None and tour not in tournaments:
                continue
            d = date.fromisoformat(row["date"].strip())
            kickoff = datetime(d.year, d.month, d.day, 12, 0, tzinfo=UTC)
            if min_date is not None and kickoff < min_date:
                continue
            home = row["home_team"].strip()
            away = row["away_team"].strip()
            home_score_raw = row["home_score"].strip()
            away_score_raw = row["away_score"].strip()
            if home_score_raw in ("", "NA") or away_score_raw in ("", "NA"):
                # Dataset uses "NA" for matches without confirmed result;
                # skip them — they cannot train Dixon-Coles or ELO.
                continue
            result.append(
                InternationalMatchDTO(
                    source_id=self.source_id,
                    external_id=f"{row['date'].strip()}_{home}_{away}".replace(" ", "_"),
                    home_team_name=home,
                    away_team_name=away,
                    home_goals=int(home_score_raw),
                    away_goals=int(away_score_raw),
                    kickoff_utc=kickoff,
                    tournament=tour,
                    city=row["city"].strip() or None,
                    host_country=row["country"].strip() or None,
                    is_neutral=row["neutral"].strip().lower() == "true",
                )
            )
        return result
