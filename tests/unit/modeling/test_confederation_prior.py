"""Tests for the confederation prior penalty + integration with the fitter."""

import random
from datetime import UTC, datetime

import pytest

from analytis.domain.confederation import Confederation
from analytis.modeling.confederation_prior import (
    ConfederationPrior,
    confederation_penalty,
)
from analytis.modeling.fitting import FitConfig, MatchObservation, fit_dixon_coles


def test_penalty_zero_when_matches_prior() -> None:
    prior = ConfederationPrior(
        team_to_confederation={"T1": Confederation.UEFA, "T2": Confederation.UEFA},
        confederation_attack_mean={Confederation.UEFA: 0.1},
        confederation_defense_mean={Confederation.UEFA: 0.05},
        sigma=0.5,
    )
    pen = confederation_penalty(
        attack={"T1": 0.1, "T2": 0.1},
        defense={"T1": 0.05, "T2": 0.05},
        prior=prior,
    )
    assert pen == pytest.approx(0.0, abs=1e-9)


def test_penalty_grows_with_deviation() -> None:
    prior = ConfederationPrior(
        team_to_confederation={"T1": Confederation.UEFA},
        confederation_attack_mean={Confederation.UEFA: 0.0},
        confederation_defense_mean={Confederation.UEFA: 0.0},
        sigma=1.0,
    )
    small = confederation_penalty(attack={"T1": 0.1}, defense={"T1": 0.0}, prior=prior)
    big = confederation_penalty(attack={"T1": 0.5}, defense={"T1": 0.0}, prior=prior)
    assert big > small


def test_unknown_confederation_skipped() -> None:
    prior = ConfederationPrior(
        team_to_confederation={"T1": Confederation.UNKNOWN},
        confederation_attack_mean={},
        confederation_defense_mean={},
        sigma=1.0,
    )
    pen = confederation_penalty(attack={"T1": 99.0}, defense={"T1": 99.0}, prior=prior)
    assert pen == pytest.approx(0.0)


def _synthetic_matches(seed: int = 1) -> list[MatchObservation]:
    rng = random.Random(seed)
    teams = ["UEFA1", "UEFA2", "CONMEBOL1", "AFC1"]
    obs: list[MatchObservation] = []
    for _ in range(10):
        for i, h in enumerate(teams):
            for j, a in enumerate(teams):
                if i == j:
                    continue
                hg = rng.randint(0, 3)
                ag = rng.randint(0, 3)
                obs.append(
                    MatchObservation(
                        home_team=h,
                        away_team=a,
                        home_goals=hg,
                        away_goals=ag,
                        kickoff_utc=datetime(2024, 1, 1, tzinfo=UTC),
                        is_neutral=False,
                    )
                )
    return obs


def test_fitter_with_prior_pulls_low_data_team_toward_prior() -> None:
    matches = _synthetic_matches()
    # Add ONE match for a low-data team, with extreme result.
    matches.append(
        MatchObservation(
            home_team="OFC_RARE",
            away_team="UEFA1",
            home_goals=9,
            away_goals=0,
            kickoff_utc=datetime(2024, 1, 2, tzinfo=UTC),
            is_neutral=False,
        )
    )
    prior = ConfederationPrior(
        team_to_confederation={
            "UEFA1": Confederation.UEFA,
            "UEFA2": Confederation.UEFA,
            "CONMEBOL1": Confederation.CONMEBOL,
            "AFC1": Confederation.AFC,
            "OFC_RARE": Confederation.OFC,
        },
        confederation_attack_mean={
            Confederation.UEFA: 0.0,
            Confederation.CONMEBOL: 0.0,
            Confederation.AFC: -0.1,
            Confederation.OFC: -0.4,
        },
        confederation_defense_mean={
            Confederation.UEFA: 0.0,
            Confederation.CONMEBOL: 0.0,
            Confederation.AFC: -0.1,
            Confederation.OFC: -0.4,
        },
        sigma=0.2,  # tight prior
    )
    cfg_no_prior = FitConfig(max_iter=200)
    cfg_with_prior = FitConfig(max_iter=200, confederation_prior=prior)
    no_prior = fit_dixon_coles(matches, config=cfg_no_prior)
    with_prior = fit_dixon_coles(matches, config=cfg_with_prior)
    # With the tight prior, OFC_RARE's attack should be MUCH closer to -0.4
    # than the unconstrained fit, which over-fits the single 9-0 result.
    assert abs(with_prior.attack["OFC_RARE"] - (-0.4)) < abs(no_prior.attack["OFC_RARE"] - (-0.4))
