"""Isotonic regression calibration wrapper around scikit-learn."""

from typing import cast

import numpy as np
from sklearn.isotonic import IsotonicRegression


class IsotonicCalibrator:
    def __init__(self, *, out_of_bounds: str = "clip") -> None:
        self._model: IsotonicRegression | None = None
        self._out_of_bounds = out_of_bounds

    def fit(self, *, probs: list[float], outcomes: list[int]) -> None:
        if len(probs) != len(outcomes):
            raise ValueError("probs and outcomes must have same length")
        x = np.array(probs, dtype=np.float64)
        y = np.array(outcomes, dtype=np.float64)
        model = IsotonicRegression(
            y_min=0.0,
            y_max=1.0,
            increasing=True,
            out_of_bounds=self._out_of_bounds,
        )
        model.fit(x, y)
        self._model = model

    def predict(self, prob: float) -> float:
        if self._model is None:
            raise RuntimeError("IsotonicCalibrator not fitted")
        arr = np.array([prob], dtype=np.float64)
        out = self._model.predict(arr)
        return float(cast(np.ndarray, out)[0])


__all__ = ["IsotonicCalibrator"]
