"""Tests for ranking corpus entries against a question."""

import numpy as np

from rules_attorney.retrieve import rank


def test_rank_orders_by_cosine() -> None:
    question = np.array([1.0, 0.0])
    entries = np.array([[0.0, 1.0], [1.0, 0.0], [1.0, 1.0]])
    assert rank(question, entries, ["far", "near", "mid"]) == ["near", "mid", "far"]


def test_rank_ignores_length() -> None:
    question = np.array([1.0, 0.0])
    entries = np.array([[1.0, 0.1], [2.0, 20.0]])
    assert rank(question, entries, ["near", "long-far"]) == ["near", "long-far"]
