"""Tests for XGBoost match classifier."""

import random

import pytest

from analytis.modeling.xgboost_classifier import (
    FeatureVectorizer,
    XGBoostMatchClassifier,
)


def test_vectorizer_learns_keys_in_sorted_order() -> None:
    v = FeatureVectorizer()
    v.fit([{"b": 1.0, "a": 2.0}, {"a": 3.0, "c": 4.0}])
    assert v.feature_names == ["a", "b", "c"]


def test_vectorizer_transform_imputes_missing() -> None:
    v = FeatureVectorizer()
    v.fit([{"a": 1.0, "b": 2.0}])
    out = v.transform([{"a": 5.0}])  # missing "b"
    assert out.shape == (1, 2)
    assert out[0, 0] == 5.0
    assert out[0, 1] == 0.0


def test_vectorizer_handles_bool_and_none() -> None:
    v = FeatureVectorizer()
    v.fit([{"flag": True, "val": None, "x": 1.5}])
    out = v.transform([{"flag": False, "val": None, "x": 2.0}])
    assert out[0, 0] == 0.0
    assert out[0, 1] == 0.0
    assert out[0, 2] == 2.0


def test_vectorizer_transform_unfitted_raises() -> None:
    v = FeatureVectorizer()
    with pytest.raises(RuntimeError, match="not fitted"):
        v.transform([{"a": 1.0}])


def _synth_1x2_dataset(
    n: int = 400, seed: int = 1
) -> tuple[list[dict[str, object]], list[tuple[int, int]]]:
    rng = random.Random(seed)
    features: list[dict[str, object]] = []
    outcomes: list[tuple[int, int]] = []
    for _ in range(n):
        elo_diff = rng.uniform(-300, 300)
        rest_diff = rng.uniform(-3, 3)
        # Higher elo_diff -> more home wins; pure signal
        p_home = 0.5 + elo_diff / 800.0
        p_home = max(0.05, min(0.85, p_home))
        roll = rng.random()
        if roll < p_home:
            h, a = rng.randint(1, 3), rng.randint(0, 1)
        elif roll < p_home + 0.2:
            h, a = rng.randint(1, 2), rng.randint(1, 2)
        else:
            h, a = rng.randint(0, 1), rng.randint(1, 3)
        features.append({"elo_diff": elo_diff, "rest_diff": rest_diff})
        outcomes.append((h, a))
    return features, outcomes


def test_classifier_1x2_above_random() -> None:
    features, outcomes = _synth_1x2_dataset(n=400)
    train_x, train_y = features[:320], outcomes[:320]
    test_x, test_y = features[320:], outcomes[320:]

    clf = XGBoostMatchClassifier(market="1x2", n_estimators=80, max_depth=3)
    clf.fit(train_x, train_y)

    correct = 0
    for f, (h, a) in zip(test_x, test_y, strict=True):
        probs = clf.predict_proba_one(f)
        pred = max(probs, key=lambda k: probs[k])
        actual = "home" if h > a else ("draw" if h == a else "away")
        if pred == actual:
            correct += 1
    # Should beat 33% random and 38% naive "always home" baseline
    assert correct / len(test_y) > 0.45


def test_classifier_ou_2_5_outputs_sum_to_one() -> None:
    features, outcomes = _synth_1x2_dataset(n=200)
    clf = XGBoostMatchClassifier(market="over_under_2_5", n_estimators=50)
    clf.fit(features, outcomes)
    probs = clf.predict_proba_one(features[0])
    assert set(probs.keys()) == {"over_2.5", "under_2.5"}
    assert probs["over_2.5"] + probs["under_2.5"] == pytest.approx(1.0, abs=1e-6)


def test_classifier_btts_outputs_sum_to_one() -> None:
    features, outcomes = _synth_1x2_dataset(n=200)
    clf = XGBoostMatchClassifier(market="btts", n_estimators=50)
    clf.fit(features, outcomes)
    probs = clf.predict_proba_one(features[0])
    assert set(probs.keys()) == {"yes", "no"}
    assert probs["yes"] + probs["no"] == pytest.approx(1.0, abs=1e-6)


def test_classifier_unfitted_raises() -> None:
    clf = XGBoostMatchClassifier(market="1x2")
    with pytest.raises(RuntimeError, match="not fitted"):
        clf.predict_proba_one({"elo_diff": 0.0})


def test_classifier_rejects_unknown_market() -> None:
    with pytest.raises(ValueError, match="unknown market"):
        XGBoostMatchClassifier(market="corners")
