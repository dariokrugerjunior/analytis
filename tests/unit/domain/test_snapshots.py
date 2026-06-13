"""Tests for inference-side entities (snapshots, model versions, predictions)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from analytis.domain.snapshots import (
    FeatureSnapshot,
    ModelVersion,
    Prediction,
    PredictionMarket,
)


def test_feature_snapshot_minimal() -> None:
    s = FeatureSnapshot(
        match_id=uuid4(),
        snapshot_taken_at=datetime(2026, 6, 15, 16, 0, tzinfo=UTC),
        features={"elo_diff": 184.0, "rest_days_home": 6.0},
    )
    assert s.features["elo_diff"] == 184.0


def test_feature_snapshot_taken_at_must_be_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        FeatureSnapshot(
            match_id=uuid4(),
            snapshot_taken_at=datetime(2026, 6, 15, 16, 0),
            features={},
        )


def test_model_version_minimal() -> None:
    mv = ModelVersion(
        name="ensemble-v0.3.1",
        family="ensemble",
        git_sha="abc1234",
        hyperparams={"learning_rate": 0.05},
        metrics={"brier_1x2": 0.21},
    )
    assert mv.is_promoted is False


def test_prediction_probability_range() -> None:
    Prediction(
        match_id=uuid4(),
        market=PredictionMarket.MATCH_RESULT,
        outcome="home",
        prob=0.527,
        ci_low=0.471,
        ci_high=0.583,
        model_version_id=uuid4(),
        feature_snapshot_id=uuid4(),
        created_at=datetime(2026, 6, 15, 16, 0, tzinfo=UTC),
    )


def test_prediction_rejects_out_of_range_prob() -> None:
    with pytest.raises(ValueError, match="less than or equal to 1"):
        Prediction(
            match_id=uuid4(),
            market=PredictionMarket.BTTS,
            outcome="yes",
            prob=1.2,
            ci_low=1.1,
            ci_high=1.3,
            model_version_id=uuid4(),
            feature_snapshot_id=uuid4(),
            created_at=datetime(2026, 6, 15, 16, 0, tzinfo=UTC),
        )


def test_prediction_rejects_ci_inverted() -> None:
    with pytest.raises(ValueError, match="ci_low must be <= ci_high"):
        Prediction(
            match_id=uuid4(),
            market=PredictionMarket.OVER_UNDER_GOALS,
            outcome="over_2.5",
            prob=0.5,
            ci_low=0.7,
            ci_high=0.3,
            model_version_id=uuid4(),
            feature_snapshot_id=uuid4(),
            created_at=datetime(2026, 6, 15, 16, 0, tzinfo=UTC),
        )
