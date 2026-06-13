"""Stacking ensemble — combines Dixon-Coles and XGBoost classifier outputs.

For each (market x outcome) we fit a logistic regression that takes the two
component probabilities as features and produces a calibrated final
probability. For 1X2 (multiclass) we fit three binary stackers and
renormalise the outputs via softmax over the logits.
"""

import math

import numpy as np
from sklearn.linear_model import LogisticRegression


def _label_1x2(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if home_goals == away_goals:
        return "draw"
    return "away"


def _label_ou(home_goals: int, away_goals: int) -> str:
    return "over_2.5" if (home_goals + away_goals) > 2 else "under_2.5"


def _label_btts(home_goals: int, away_goals: int) -> str:
    return "yes" if (home_goals >= 1 and away_goals >= 1) else "no"


_MARKET_OUTCOMES: dict[str, tuple[str, ...]] = {
    "1x2": ("home", "draw", "away"),
    "over_under_2_5": ("over_2.5", "under_2.5"),
    "btts": ("yes", "no"),
}


def _market_label(market: str, home_goals: int, away_goals: int) -> str:
    if market == "1x2":
        return _label_1x2(home_goals, away_goals)
    if market == "over_under_2_5":
        return _label_ou(home_goals, away_goals)
    return _label_btts(home_goals, away_goals)


class StackingEnsemble:
    """Logistic-regression stacker over (DC prob, XGBoost prob) per outcome."""

    def __init__(self, *, market: str) -> None:
        if market not in _MARKET_OUTCOMES:
            raise ValueError(f"unknown market {market!r}")
        self._market = market
        self._models: dict[str, LogisticRegression] = {}
        self._fitted = False

    def fit(
        self,
        dc_probs: list[dict[str, float]],
        xgb_probs: list[dict[str, float]],
        outcomes: list[tuple[int, int]],
    ) -> None:
        if not (len(dc_probs) == len(xgb_probs) == len(outcomes)):
            raise ValueError("dc_probs, xgb_probs, outcomes must have same length")
        if not dc_probs:
            raise ValueError("at least one training sample required")
        outcome_keys = _MARKET_OUTCOMES[self._market]
        for outcome in outcome_keys:
            features: list[list[float]] = []
            labels: list[int] = []
            for dc, xg, (h, a) in zip(dc_probs, xgb_probs, outcomes, strict=True):
                features.append([dc.get(outcome, 0.0), xg.get(outcome, 0.0)])
                labels.append(1 if _market_label(self._market, h, a) == outcome else 0)
            if len(set(labels)) < 2:
                # Degenerate case: outcome never occurred or always occurred.
                # Use a zero-intercept identity model that returns the mean of dc/xgb.
                self._models[outcome] = _IdentityFallback(base_rate=float(np.mean(labels)))
                continue
            model = LogisticRegression(max_iter=1000, C=1.0)
            model.fit(np.array(features, dtype=np.float64), np.array(labels))
            self._models[outcome] = model
        self._fitted = True

    def predict_one(
        self,
        dc_probs: dict[str, float],
        xgb_probs: dict[str, float],
    ) -> dict[str, float]:
        if not self._fitted:
            raise RuntimeError("ensemble not fitted")
        outcome_keys = _MARKET_OUTCOMES[self._market]
        raw: dict[str, float] = {}
        for outcome in outcome_keys:
            model = self._models[outcome]
            x = np.array(
                [[dc_probs.get(outcome, 0.0), xgb_probs.get(outcome, 0.0)]],
                dtype=np.float64,
            )
            p = float(model.predict_proba(x)[0][1])
            raw[outcome] = max(1e-9, min(1.0 - 1e-9, p))
        total = sum(raw.values())
        if total <= 0:
            uniform = 1.0 / len(outcome_keys)
            return dict.fromkeys(outcome_keys, uniform)
        return {k: v / total for k, v in raw.items()}


class _IdentityFallback:
    """Fallback when one outcome never appears in training: return base rate."""

    def __init__(self, base_rate: float) -> None:
        self._base = max(1e-6, min(1.0 - 1e-6, base_rate))

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        n = x.shape[0]
        out = np.zeros((n, 2), dtype=np.float64)
        out[:, 0] = 1.0 - self._base
        out[:, 1] = self._base
        return out


# softmax helper kept for potential future use
def _softmax(logits: list[float]) -> list[float]:
    m = max(logits)
    exps = [math.exp(x - m) for x in logits]
    s = sum(exps)
    return [e / s for e in exps]


__all__ = ["StackingEnsemble"]
