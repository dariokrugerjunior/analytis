"""Tests for walk-forward CV slicing."""

from datetime import UTC, datetime, timedelta

import pytest

from analytis.modeling.walk_forward import (
    WalkForwardSlice,
    iter_walk_forward_slices,
)


def _matches(n: int, start: datetime) -> list[datetime]:
    return [start + timedelta(days=i) for i in range(n)]


def test_slices_basic() -> None:
    times = _matches(30, datetime(2024, 1, 1, tzinfo=UTC))
    slices = list(iter_walk_forward_slices(times, min_train_size=10, test_size=5, key=lambda t: t))
    # After warm-up: (10, 11..15), (15, 16..20), (20, 21..25), (25, 26..30)
    assert len(slices) == 4
    s0 = slices[0]
    assert s0.train_end_idx == 10
    assert s0.test_start_idx == 10
    assert s0.test_end_idx == 15


def test_slices_test_size_validation() -> None:
    times = _matches(10, datetime(2024, 1, 1, tzinfo=UTC))
    with pytest.raises(ValueError, match="test_size must be positive"):
        list(iter_walk_forward_slices(times, min_train_size=5, test_size=0, key=lambda t: t))


def test_slices_min_train_validation() -> None:
    times = _matches(10, datetime(2024, 1, 1, tzinfo=UTC))
    with pytest.raises(ValueError, match="min_train_size must be positive"):
        list(iter_walk_forward_slices(times, min_train_size=0, test_size=2, key=lambda t: t))


def test_slices_insufficient_data_returns_empty() -> None:
    times = _matches(3, datetime(2024, 1, 1, tzinfo=UTC))
    slices = list(iter_walk_forward_slices(times, min_train_size=10, test_size=5, key=lambda t: t))
    assert slices == []


def test_slices_unsorted_raises() -> None:
    times = _matches(20, datetime(2024, 1, 1, tzinfo=UTC))
    times[5], times[10] = times[10], times[5]  # break ordering
    with pytest.raises(ValueError, match="chronological"):
        list(iter_walk_forward_slices(times, min_train_size=5, test_size=3, key=lambda t: t))


def test_slice_includes_indices_and_keys() -> None:
    times = _matches(20, datetime(2024, 1, 1, tzinfo=UTC))
    slices = list(iter_walk_forward_slices(times, min_train_size=8, test_size=4, key=lambda t: t))
    s0 = slices[0]
    assert isinstance(s0, WalkForwardSlice)
    assert s0.train_end_key == times[7]  # last train sample
    assert s0.test_start_key == times[8]
    assert s0.test_end_key == times[11]  # last test sample
