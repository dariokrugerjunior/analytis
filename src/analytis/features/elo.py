"""World Football Elo math primitives.

Adapted from the formula at https://www.eloratings.net/about — key choices:
- Logistic with scale 400.
- Home advantage 100 (subtractable to zero for neutral venues).
- Goal-difference multiplier as on eloratings.net.
- K-factor scaled by competition importance.
"""

import math

DEFAULT_RATING: float = 1500.0
HOME_ADVANTAGE: float = 100.0

_TOURNAMENT_K: dict[str, float] = {
    "FIFA World Cup": 60.0,
    "Copa America": 50.0,
    "UEFA Euro": 50.0,
    "African Cup of Nations": 50.0,
    "AFC Asian Cup": 50.0,
    "FIFA World Cup qualification": 40.0,
    "UEFA Nations League": 40.0,
    "Confederations Cup": 40.0,
    "Friendly": 20.0,
}
_DEFAULT_K: float = 20.0


def k_factor(tournament: str) -> float:
    return _TOURNAMENT_K.get(tournament, _DEFAULT_K)


def expected_score(rating_a: float, rating_b: float, home_advantage: float = 0.0) -> float:
    """Logistic expected score for player A against B (scale 400)."""
    diff = rating_a + home_advantage - rating_b
    return 1.0 / (1.0 + math.pow(10.0, -diff / 400.0))


def _goal_diff_multiplier(goal_diff: int) -> float:
    g = abs(goal_diff)
    if g <= 1:
        return 1.0
    if g == 2:
        return 1.5
    return (11.0 + g) / 8.0


def _outcome(home_goals: int, away_goals: int) -> float:
    if home_goals > away_goals:
        return 1.0
    if home_goals < away_goals:
        return 0.0
    return 0.5


def update_ratings(
    home_rating: float,
    away_rating: float,
    home_goals: int,
    away_goals: int,
    tournament: str,
    is_neutral: bool,
) -> tuple[float, float]:
    """Return new (home_rating, away_rating) after a single match."""
    ha = 0.0 if is_neutral else HOME_ADVANTAGE
    es = expected_score(home_rating, away_rating, home_advantage=ha)
    actual = _outcome(home_goals, away_goals)
    k = k_factor(tournament) * _goal_diff_multiplier(home_goals - away_goals)
    delta = k * (actual - es)
    return home_rating + delta, away_rating - delta
