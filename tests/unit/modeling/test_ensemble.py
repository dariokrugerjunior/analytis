"""Tests for the stacking ensemble."""

import random

import pytest

from analytis.modeling.ensemble import StackingEnsemble


def test_ensemble_rejects_bad_market() -> None:
    with pytest.raises(ValueError, match="unknown market"):
        StackingEnsemble(market="corners")


def test_ensemble_unfitted_raises() -> None:
    ens = StackingEnsemble(market="1x2")
    with pytest.raises(RuntimeError, match="not fitted"):
        ens.predict_one({"home": 0.5}, {"home": 0.5})


def _synth_aligned(
    n: int = 200, seed: int = 1
) -> tuple[list[dict[str, float]], list[dict[str, float]], list[tuple[int, int]]]:
    """Both models agree on signal; ensemble should converge to the truth."""
    rng = random.Random(seed)
    dc: list[dict[str, float]] = []
    xg: list[dict[str, float]] = []
    out: list[tuple[int, int]] = []
    for _ in range(n):
        p = rng.uniform(0.2, 0.8)
        home = 1 if rng.random() < p else 0
        dc.append({"home": p, "draw": 0.2, "away": 1.0 - p - 0.2})
        xg.append({"home": p, "draw": 0.2, "away": 1.0 - p - 0.2})
        h, a = (2, 0) if home == 1 else (0, 2)
        out.append((h, a))
    return dc, xg, out


def test_ensemble_1x2_sums_to_one() -> None:
    dc, xg, outcomes = _synth_aligned(n=200)
    ens = StackingEnsemble(market="1x2")
    ens.fit(dc, xg, outcomes)
    probs = ens.predict_one(dc[0], xg[0])
    assert set(probs.keys()) == {"home", "draw", "away"}
    assert sum(probs.values()) == pytest.approx(1.0, abs=1e-6)


def test_ensemble_ou_sums_to_one() -> None:
    dc, xg, outcomes = _synth_aligned(n=200)
    # convert outcomes to OU labels via goals already in synth
    ens = StackingEnsemble(market="over_under_2_5")
    # build dc/xgb probs for OU
    dc_ou = [{"over_2.5": 0.4, "under_2.5": 0.6} for _ in dc]
    xg_ou = [{"over_2.5": 0.4, "under_2.5": 0.6} for _ in xg]
    ens.fit(dc_ou, xg_ou, outcomes)
    p = ens.predict_one(dc_ou[0], xg_ou[0])
    assert p["over_2.5"] + p["under_2.5"] == pytest.approx(1.0, abs=1e-6)


def test_ensemble_btts_sums_to_one() -> None:
    dc, xg, outcomes = _synth_aligned(n=200)
    dc_b = [{"yes": 0.5, "no": 0.5} for _ in dc]
    xg_b = [{"yes": 0.5, "no": 0.5} for _ in xg]
    ens = StackingEnsemble(market="btts")
    ens.fit(dc_b, xg_b, outcomes)
    p = ens.predict_one(dc_b[0], xg_b[0])
    assert p["yes"] + p["no"] == pytest.approx(1.0, abs=1e-6)


def test_ensemble_can_recover_dc_when_xgb_useless() -> None:
    """If XGB is pure noise, the stacker should down-weight it and
    follow DC closely (sanity, not exact)."""
    rng = random.Random(7)
    dc: list[dict[str, float]] = []
    xg: list[dict[str, float]] = []
    outcomes: list[tuple[int, int]] = []
    for _ in range(300):
        p_home = rng.uniform(0.1, 0.9)
        dc.append({"home": p_home, "draw": 0.15, "away": 0.85 - p_home})
        # noise for xgb
        xg.append({"home": rng.random(), "draw": rng.random(), "away": rng.random()})
        # realise outcome from DC
        roll = rng.random()
        if roll < p_home:
            outcomes.append((2, 0))
        elif roll < p_home + 0.15:
            outcomes.append((1, 1))
        else:
            outcomes.append((0, 2))

    ens = StackingEnsemble(market="1x2")
    ens.fit(dc, xg, outcomes)

    # Test prediction on a strong-home scenario
    probs = ens.predict_one(
        {"home": 0.7, "draw": 0.15, "away": 0.15},
        {"home": 0.5, "draw": 0.3, "away": 0.2},
    )
    # Strong home should remain the biggest outcome
    assert probs["home"] > probs["draw"]
    assert probs["home"] > probs["away"]
