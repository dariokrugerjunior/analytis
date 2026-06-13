"""Expected value math primitives."""


def implied_probability(decimal_odds: float) -> float:
    if decimal_odds < 1.01:
        raise ValueError("decimal_odds must be >= 1.01")
    return 1.0 / decimal_odds


def edge(*, our_prob: float, decimal_odds: float) -> float:
    """Expected unit-stake profit per bet.

    edge = our_prob * (odds - 1) - (1 - our_prob)
    Positive means +EV under our prob.
    """
    if not 0.0 <= our_prob <= 1.0:
        raise ValueError("our_prob must be in [0, 1]")
    if decimal_odds < 1.01:
        raise ValueError("decimal_odds must be >= 1.01")
    return our_prob * (decimal_odds - 1.0) - (1.0 - our_prob)


def remove_overround(decimal_odds_list: list[float]) -> list[float]:
    """Naive proportional overround removal (additive method).
    Returns implied 'fair' probabilities that sum to 1.0.
    """
    if not decimal_odds_list:
        raise ValueError("decimal_odds_list must not be empty")
    implied = [implied_probability(o) for o in decimal_odds_list]
    total = sum(implied)
    if total <= 0:
        raise ValueError("implied probabilities sum to <= 0")
    return [p / total for p in implied]


__all__ = ["edge", "implied_probability", "remove_overround"]
