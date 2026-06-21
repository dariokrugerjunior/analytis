from analytis.push.bodies import build_post_payload, build_pre_payload


def _fake_match(
    *,
    home: str = "Brazil",
    away: str = "Argentina",
    match_id: str = "abc-uuid",
    home_goals: int | None = None,
    away_goals: int | None = None,
) -> dict[str, str | int | None]:
    return {
        "id": match_id,
        "home_team": home,
        "away_team": away,
        "home_goals": home_goals,
        "away_goals": away_goals,
    }


def _fake_probs_home_win() -> dict[str, float]:
    return {"home": 0.55, "draw": 0.25, "away": 0.20}


def test_build_pre_payload_home_win() -> None:
    match = _fake_match()
    payload = build_pre_payload(match, _fake_probs_home_win())
    assert "Brazil" in payload["title"]
    assert "Argentina" in payload["title"]
    assert "10 min" in payload["title"] or "10min" in payload["title"]
    assert "55" in payload["body"]
    assert payload["url"] == "/matches/abc-uuid"


def test_build_pre_payload_draw_probs() -> None:
    match = _fake_match()
    payload = build_pre_payload(match, {"home": 0.32, "draw": 0.42, "away": 0.26})
    assert "42" in payload["body"]


def test_build_post_payload_correct_winner() -> None:
    match = _fake_match(home_goals=2, away_goals=1)
    payload = build_post_payload(match, _fake_probs_home_win())
    assert "2-1" in payload["title"] or "2 - 1" in payload["title"]
    assert "Brazil" in payload["title"]
    assert payload["url"] == "/matches/abc-uuid"
    assert "✓" in payload["body"] or "acerto" in payload["body"].lower()


def test_build_post_payload_wrong_winner() -> None:
    match = _fake_match(home_goals=0, away_goals=2)
    payload = build_post_payload(match, _fake_probs_home_win())
    assert "✗" in payload["body"] or "errou" in payload["body"].lower()
