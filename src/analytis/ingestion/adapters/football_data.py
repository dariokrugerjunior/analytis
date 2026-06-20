"""Adapter for the Football-Data.org REST API (free tier)."""

from collections.abc import Iterable
from datetime import datetime
from typing import Any

import httpx

from analytis.ingestion.ports import CompetitionDTO, MatchDTO
from analytis.ingestion.rate_limiter import TokenBucket
from analytis.ingestion.retry import with_retry

_STATUS_MAP = {
    "SCHEDULED": "scheduled",
    "TIMED": "scheduled",
    "LIVE": "live",
    "IN_PLAY": "live",
    "PAUSED": "live",
    "FINISHED": "finished",
    "POSTPONED": "postponed",
    "SUSPENDED": "postponed",
    "CANCELLED": "cancelled",
    "AWARDED": "finished",
}

_INTERNATIONAL_CUP_CODES = {"WC", "EC", "CA", "AFCON"}


class FootballDataAdapter:
    """Adapter implementing DataSourceAdapter for Football-Data.org v4."""

    source_id = "footballdata"
    BASE_URL = "https://api.football-data.org/v4"

    def __init__(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        rate_limit_per_minute: int = 10,
    ) -> None:
        self._client = client
        self._headers = {"X-Auth-Token": api_key}
        self._bucket = TokenBucket(
            rate_per_second=rate_limit_per_minute / 60.0,
            capacity=max(1, rate_limit_per_minute),
        )

    @with_retry(max_attempts=3, base_delay=1.0, max_delay=15.0)
    async def _get(self, path: str, **params: Any) -> dict[str, Any]:
        await self._bucket.acquire()
        response = await self._client.get(path, headers=self._headers, params=params)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    async def fetch_competitions(self) -> Iterable[CompetitionDTO]:
        data = await self._get("/competitions")
        result = []
        for c in data.get("competitions", []):
            code = (c.get("code") or "").upper()
            ctype = (
                "selecao" if code in _INTERNATIONAL_CUP_CODES or c.get("type") == "CUP" else "clube"
            )
            result.append(
                CompetitionDTO(
                    source_id=self.source_id,
                    external_id=str(c["id"]),
                    name=c["name"],
                    slug=code.lower() or _slugify(c["name"]),
                    competition_type=ctype,
                    country=(c.get("area") or {}).get("code") or "UNK",
                )
            )
        return result

    async def fetch_matches(
        self, competition_external_id: str, season_label: str
    ) -> Iterable[MatchDTO]:
        data = await self._get(
            f"/competitions/{competition_external_id}/matches",
            season=season_label,
        )
        is_intl_cup = self._is_international_cup(competition_external_id)
        result: list[MatchDTO] = []
        for m in data.get("matches", []):
            ref = next(
                (r["name"] for r in m.get("referees", []) if r.get("role") == "REFEREE"),
                None,
            )
            full = m.get("score", {}).get("fullTime", {}) or {}
            home = m["homeTeam"]
            away = m["awayTeam"]
            if not home.get("name") or not away.get("name"):
                # Knockout placeholders ("Winner Group A vs Runner-up Group B")
                # have null team names; skip until the bracket resolves.
                continue
            result.append(
                MatchDTO(
                    source_id=self.source_id,
                    external_id=str(m["id"]),
                    competition_external_id=competition_external_id,
                    season_label=season_label,
                    home_team_external_id=str(home["id"]),
                    home_team_name=home["name"],
                    home_team_short_name=(home.get("tla") or home["name"][:5]).upper(),
                    away_team_external_id=str(away["id"]),
                    away_team_name=away["name"],
                    away_team_short_name=(away.get("tla") or away["name"][:5]).upper(),
                    kickoff_utc=_parse_iso(m["utcDate"]),
                    is_home_neutral=is_intl_cup,
                    status=_STATUS_MAP.get(m["status"], "scheduled"),
                    stage=m.get("stage"),
                    home_goals=full.get("home"),
                    away_goals=full.get("away"),
                    home_corners=None,
                    away_corners=None,
                    venue_name=m.get("venue"),
                    referee_name=ref,
                )
            )
        return result

    async def fetch_seasons(self, competition_external_id: str) -> Iterable[Any]:
        raise NotImplementedError("Football-Data exposes seasons via competition payload")

    async def fetch_teams(self, competition_external_id: str) -> Iterable[Any]:
        raise NotImplementedError("Use fetch_matches; teams are inferred from matches")

    def _is_international_cup(self, competition_external_id: str) -> bool:
        # Football-Data id 2000 = FIFA World Cup. Extend list if you add EC/CA/AFCON.
        return competition_external_id in {"2000"}


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _slugify(value: str) -> str:
    return "-".join(value.lower().split())
