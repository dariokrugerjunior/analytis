"""Walk-forward cross-validation slicing.

Given a chronologically-sorted iterable of records (matches, snapshots,
whatever), yields (train_window, test_window) index ranges in order:

    slice 0: train = records[0 : min_train_size]
             test  = records[min_train_size : min_train_size + test_size]
    slice 1: train = records[0 : min_train_size + test_size]
             test  = records[min_train_size + test_size : ... + test_size]
    ... and so on until exhausted.

The caller is responsible for materialising the train/test subsets using
the indices on the slice.
"""

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WalkForwardSlice:
    train_end_idx: int  # exclusive (matches[:train_end_idx] = train set)
    test_start_idx: int
    test_end_idx: int  # exclusive
    train_end_key: Any
    test_start_key: Any
    test_end_key: Any


def iter_walk_forward_slices[T, K](
    records: Sequence[T],
    *,
    min_train_size: int,
    test_size: int,
    key: Callable[[T], K],
) -> Iterator[WalkForwardSlice]:
    if min_train_size <= 0:
        raise ValueError("min_train_size must be positive")
    if test_size <= 0:
        raise ValueError("test_size must be positive")

    n = len(records)
    if n == 0:
        return

    last_key = key(records[0])
    for i in range(1, n):
        cur_key = key(records[i])
        if cur_key < last_key:  # type: ignore[operator]
            raise ValueError("records must be in chronological order by key")
        last_key = cur_key

    train_end = min_train_size
    while train_end + test_size <= n:
        test_end = train_end + test_size
        yield WalkForwardSlice(
            train_end_idx=train_end,
            test_start_idx=train_end,
            test_end_idx=test_end,
            train_end_key=key(records[train_end - 1]),
            test_start_key=key(records[train_end]),
            test_end_key=key(records[test_end - 1]),
        )
        train_end = test_end


__all__ = ["WalkForwardSlice", "iter_walk_forward_slices"]
