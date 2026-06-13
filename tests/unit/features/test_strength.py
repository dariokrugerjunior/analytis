"""Tests for team strength features (attack/defense w/ shrinkage)."""

import pytest

from analytis.features.strength import (
    MatchSample,
    StrengthPrior,
    shrunk_attack_per_90,
    shrunk_defense_per_90,
)

_PRIOR = StrengthPrior(attack_per_90=1.2, defense_per_90=1.2, prior_strength=5.0)


def test_no_history_returns_prior() -> None:
    attack = shrunk_attack_per_90(history=[], prior=_PRIOR)
    defense = shrunk_defense_per_90(history=[], prior=_PRIOR)
    assert attack == pytest.approx(_PRIOR.attack_per_90)
    assert defense == pytest.approx(_PRIOR.defense_per_90)


def test_many_games_dominates_prior() -> None:
    # 50 games, 2.0 goals scored per game, 0.5 conceded.
    history = [MatchSample(goals_for=2, goals_against=0, minutes_played=90) for _ in range(50)]
    attack = shrunk_attack_per_90(history=history, prior=_PRIOR)
    defense = shrunk_defense_per_90(history=history, prior=_PRIOR)
    # Expected attack: (50 * 2.0 + 5 * 1.2) / (50 + 5) = (100 + 6) / 55 = 1.927...
    assert attack == pytest.approx(1.927, abs=1e-3)
    # Expected defense: (50 * 0.0 + 5 * 1.2) / 55 = 0.109...
    assert defense == pytest.approx(0.109, abs=1e-3)


def test_few_games_pulled_toward_prior() -> None:
    # 1 game, 5 goals scored — without shrinkage this would be a wild 5.0.
    history = [MatchSample(goals_for=5, goals_against=0, minutes_played=90)]
    attack = shrunk_attack_per_90(history=history, prior=_PRIOR)
    # Expected attack: (1 * 5.0 + 5 * 1.2) / (1 + 5) = 11.0 / 6 = 1.833...
    assert attack == pytest.approx(1.833, abs=1e-3)


def test_prior_strength_zero_means_no_shrinkage() -> None:
    flat_prior = StrengthPrior(attack_per_90=1.2, defense_per_90=1.2, prior_strength=0.0)
    history = [MatchSample(goals_for=3, goals_against=1, minutes_played=90)]
    attack = shrunk_attack_per_90(history=history, prior=flat_prior)
    assert attack == pytest.approx(3.0)


def test_per_90_handles_partial_minutes() -> None:
    # 1 game ending at 45 minutes with 1 goal: 2.0 goals per 90 minutes.
    history = [MatchSample(goals_for=1, goals_against=0, minutes_played=45)]
    flat_prior = StrengthPrior(attack_per_90=1.2, defense_per_90=1.2, prior_strength=0.0)
    attack = shrunk_attack_per_90(history=history, prior=flat_prior)
    assert attack == pytest.approx(2.0)


def test_zero_minutes_treated_as_no_data() -> None:
    history = [MatchSample(goals_for=0, goals_against=0, minutes_played=0)]
    attack = shrunk_attack_per_90(history=history, prior=_PRIOR)
    assert attack == pytest.approx(_PRIOR.attack_per_90)
