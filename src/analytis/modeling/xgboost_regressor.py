"""XGBoost regressors for expected goals (lambda_home, lambda_away).

Trains one XGBRegressor per side over the feature vector and observed goal
count. Predictions act as Poisson-rate estimates and can be converted into a
score matrix via the existing Dixon-Coles primitives.
"""

import numpy as np
import xgboost as xgb

from analytis.modeling.xgboost_classifier import FeatureVectorizer


class XGBoostGoalsRegressor:
    """Predicts the Poisson rate (expected goals) for one side of a match."""

    def __init__(
        self,
        *,
        side: str,
        n_estimators: int = 300,
        max_depth: int = 4,
        learning_rate: float = 0.05,
        random_state: int = 42,
    ) -> None:
        if side not in ("home", "away"):
            raise ValueError(f"side must be 'home' or 'away', got {side!r}")
        self._side = side
        self._vectoriser = FeatureVectorizer()
        self._model = xgb.XGBRegressor(
            objective="count:poisson",
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=random_state,
            eval_metric="rmse",
            tree_method="hist",
        )
        self._fitted = False

    def _label(self, home_goals: int, away_goals: int) -> int:
        return home_goals if self._side == "home" else away_goals

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
        y_train = np.array([self._label(h, a) for (h, a) in outcomes], dtype=np.float64)
        self._model.fit(x_train, y_train)
        self._fitted = True

    def predict_one(self, features: dict[str, object]) -> float:
        if not self._fitted:
            raise RuntimeError("regressor not fitted")
        x_pred = self._vectoriser.transform([features])
        # count:poisson outputs log-rate; XGBoost applies exp internally so the
        # returned prediction is already a non-negative expected count.
        prediction = float(self._model.predict(x_pred)[0])
        return max(0.05, prediction)


__all__ = ["XGBoostGoalsRegressor"]
