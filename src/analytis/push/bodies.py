"""Build push notification payloads (title/body/url) from match + prediction data."""

from __future__ import annotations

from typing import Any


def _top_1x2(probs: dict[str, float]) -> tuple[str, float]:
    """Return (outcome, prob) of highest 1x2 probability."""
    return max(probs.items(), key=lambda kv: kv[1])


_OUTCOME_LABEL = {
    "home": "vitória mandante",
    "draw": "empate",
    "away": "vitória visitante",
}


def build_pre_payload(match: dict[str, Any], probs_1x2: dict[str, float]) -> dict[str, str]:
    """Pre-game payload, 10 min before kickoff."""
    home = match["home_team"]
    away = match["away_team"]

    def pct(k: str) -> str:
        return f"{int(round(probs_1x2[k] * 100))}%"

    body = f"{home} {pct('home')} · empate {pct('draw')} · {away} {pct('away')}"
    return {
        "title": f"{home} x {away} em 10 min",
        "body": body,
        "url": f"/matches/{match['id']}",
    }


def build_post_payload(match: dict[str, Any], probs_1x2: dict[str, float]) -> dict[str, str]:
    """Post-game payload, right after match ends."""
    home = match["home_team"]
    away = match["away_team"]
    hg = match["home_goals"]
    ag = match["away_goals"]
    if hg is None or ag is None:
        raise ValueError("post payload requires finished match with goals")

    actual = "home" if hg > ag else ("away" if hg < ag else "draw")
    top_outcome, top_prob = _top_1x2(probs_1x2)

    marker = "✓ acerto 1X2" if top_outcome == actual else "✗ errou 1X2"
    body = (
        f"Sua previsão: {_OUTCOME_LABEL[top_outcome]} "
        f"({int(round(top_prob * 100))}%) — {marker}"
    )
    return {
        "title": f"{home} {hg}-{ag} {away}",
        "body": body,
        "url": f"/matches/{match['id']}",
    }
