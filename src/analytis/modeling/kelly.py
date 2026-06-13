"""Fractional Kelly criterion stake sizing."""


def kelly_fraction(*, our_prob: float, decimal_odds: float) -> float:
    """Optimal fraction of bankroll for a single bet under Kelly.

    f* = (b*p - q) / b, where b = odds - 1, p = our_prob, q = 1 - p.
    Negative result is clamped to 0 (don't bet).
    """
    if not 0.0 <= our_prob <= 1.0:
        raise ValueError("our_prob must be in [0, 1]")
    if decimal_odds < 1.01:
        raise ValueError("decimal_odds must be >= 1.01")
    b = decimal_odds - 1.0
    p = our_prob
    q = 1.0 - p
    f_star = (b * p - q) / b
    return max(0.0, f_star)


def kelly_stake_units(
    *,
    our_prob: float,
    decimal_odds: float,
    bankroll: float,
    fraction: float = 0.25,
    max_units: float | None = None,
) -> float:
    """Stake in absolute units. Uses *fractional* Kelly to reduce variance.

    fraction=0.25 is the common "quarter Kelly" conservative choice.
    """
    if bankroll <= 0:
        raise ValueError("bankroll must be positive")
    if not 0.0 < fraction <= 1.0:
        raise ValueError("fraction must be in (0, 1]")
    f = kelly_fraction(our_prob=our_prob, decimal_odds=decimal_odds)
    units = bankroll * f * fraction
    if max_units is not None and units > max_units:
        return max_units
    return units


__all__ = ["kelly_fraction", "kelly_stake_units"]
