"""FIFA confederation hierarchical prior for Dixon-Coles parameters.

For each team with a known confederation, the penalty term is:

    ((attack_team - mu_attack_conf)^2 + (defense_team - mu_defense_conf)^2) / sigma^2

Teams in Confederation.UNKNOWN are exempt (no prior pull).
"""

from dataclasses import dataclass

from analytis.domain.confederation import Confederation


@dataclass(frozen=True)
class ConfederationPrior:
    team_to_confederation: dict[str, Confederation]
    confederation_attack_mean: dict[Confederation, float]
    confederation_defense_mean: dict[Confederation, float]
    sigma: float = 0.3

    def is_active(self) -> bool:
        return bool(self.team_to_confederation)


def confederation_penalty(
    *,
    attack: dict[str, float],
    defense: dict[str, float],
    prior: ConfederationPrior,
) -> float:
    if prior.sigma <= 0:
        raise ValueError("sigma must be positive")
    if not prior.is_active():
        return 0.0
    total = 0.0
    sigma_sq = prior.sigma * prior.sigma
    for team, conf in prior.team_to_confederation.items():
        if conf is Confederation.UNKNOWN:
            continue
        mu_a = prior.confederation_attack_mean.get(conf)
        mu_d = prior.confederation_defense_mean.get(conf)
        if mu_a is None or mu_d is None:
            continue
        if team not in attack or team not in defense:
            continue
        total += (attack[team] - mu_a) ** 2 / sigma_sq
        total += (defense[team] - mu_d) ** 2 / sigma_sq
    return total


__all__ = ["ConfederationPrior", "confederation_penalty"]
