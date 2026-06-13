"""XGBoost classifiers for football markets (1X2, OU 2.5, BTTS).

Wraps `xgboost.XGBClassifier` with a feature-vectoriser that converts the
feature dicts produced by the Plan 2 FeatureBuilder into numerical arrays.
None values are imputed with 0.0; bools are cast to 0/1; floats kept as-is.
Unknown keys at predict time are ignored; missing keys imputed with 0.0.
"""

from dataclasses import dataclass, field

import numpy as np
import xgboost as xgb
from numpy.typing import NDArray


@dataclass
class FeatureVectorizer:
    """Learns a stable ordering of feature names from training data.

    Use `fit(features)` once with the training feature dicts; then
    `transform(features)` produces a numpy array of shape (n_samples, n_features).
    """

    feature_names: list[str] = field(default_factory=list)

    def fit(self, features: list[dict[str, object]]) -> "FeatureVectorizer":
        seen: set[str] = set()
        for f in features:
            for k in f:
                seen.add(k)
        self.feature_names = sorted(seen)
        return self

    def transform(self, features: list[dict[str, object]]) -> NDArray[np.float64]:
        if not self.feature_names:
            raise RuntimeError("FeatureVectorizer not fitted")
        n_rows = len(features)
        n_cols = len(self.feature_names)
        out = np.zeros((n_rows, n_cols), dtype=np.float64)
        for i, row in enumerate(features):
            for j, name in enumerate(self.feature_names):
                v = row.get(name)
                if v is None:
                    out[i, j] = 0.0
                elif isinstance(v, bool):
                    out[i, j] = 1.0 if v else 0.0
                else:
                    try:
                        out[i, j] = float(v)  # type: ignore[arg-type]
                    except (TypeError, ValueError):
                        out[i, j] = 0.0
        return out


_OUTCOMES_1X2 = ("home", "draw", "away")
_OUTCOMES_BINARY = ("yes", "no")
_OUTCOMES_OU = ("over_2.5", "under_2.5")


def _outcome_1x2(home_goals: int, away_goals: int) -> int:
    if home_goals > away_goals:
        return 0
    if home_goals == away_goals:
        return 1
    return 2


def _outcome_ou_2_5(home_goals: int, away_goals: int) -> int:
    return 0 if (home_goals + away_goals) > 2 else 1


def _outcome_btts(home_goals: int, away_goals: int) -> int:
    return 0 if (home_goals >= 1 and away_goals >= 1) else 1


class XGBoostMatchClassifier:
    """XGBoost classifier for one of: 1x2, over_under_2_5, btts.

    Builds the label from the (home_goals, away_goals) tuple. Outputs are
    per-outcome probabilities matching the convention used elsewhere.
    """

    def __init__(
        self,
        *,
        market: str,
        n_estimators: int = 200,
        max_depth: int = 4,
        learning_rate: float = 0.05,
        random_state: int = 42,
    ) -> None:
        if market not in ("1x2", "over_under_2_5", "btts"):
            raise ValueError(f"unknown market {market!r}")
        self._market = market
        self._vectoriser = FeatureVectorizer()
        n_class = 3 if market == "1x2" else 2
        self._model = xgb.XGBClassifier(
            objective="multi:softprob" if n_class == 3 else "binary:logistic",
            num_class=n_class if n_class == 3 else None,
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=random_state,
            eval_metric="mlogloss" if n_class == 3 else "logloss",
            tree_method="hist",
        )
        self._fitted = False

    def _label(self, home_goals: int, away_goals: int) -> int:
        if self._market == "1x2":
            return _outcome_1x2(home_goals, away_goals)
        if self._market == "over_under_2_5":
            return _outcome_ou_2_5(home_goals, away_goals)
        return _outcome_btts(home_goals, away_goals)

    def fit(
        self,
        features: list[dict[str, object]],
        outcomes: list[tuple[int, int]],
    ) -> None:
        if len(features) != len(outcomes):
            raise ValueError("features and outcomes must have same length")
        if not features:
            raise ValueError("at least one training sample required")
        self._vectoriser.fit(features)
        x_train = self._vectoriser.transform(features)
        y_train = np.array([self._label(h, a) for (h, a) in outcomes], dtype=np.int64)
        self._model.fit(x_train, y_train)
        self._fitted = True

    def predict_proba_one(self, features: dict[str, object]) -> dict[str, float]:
        if not self._fitted:
            raise RuntimeError("classifier not fitted")
        x_pred = self._vectoriser.transform([features])
        probs = self._model.predict_proba(x_pred)[0]
        if self._market == "1x2":
            return {o: float(probs[i]) for i, o in enumerate(_OUTCOMES_1X2)}
        if self._market == "over_under_2_5":
            # XGB binary: probs = [P(under), P(over)] (class 0 = under by convention?)
            # We trained class 0 = over (see _outcome_ou_2_5), so probs[0]=P(over).
            return {_OUTCOMES_OU[0]: float(probs[1]), _OUTCOMES_OU[1]: float(probs[0])}
        # btts: class 0 = yes
        return {_OUTCOMES_BINARY[0]: float(probs[1]), _OUTCOMES_BINARY[1]: float(probs[0])}


__all__ = [
    "FeatureVectorizer",
    "XGBoostMatchClassifier",
]
