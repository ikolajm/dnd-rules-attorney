"""Tests for scoring retrieval against gold cites."""

from rules_attorney.metrics import all_cites_at_k, recall_at_k


def test_recall_at_k_counts_the_share_of_cites() -> None:
    assert recall_at_k(["a", "b", "c", "d", "e"], ["b", "e"], 3) == 0.5


def test_recall_at_k_stops_at_k() -> None:
    ranked = ["a", "b", "c"]
    assert recall_at_k(ranked, ["c"], 2) == 0.0
    assert recall_at_k(ranked, ["c"], 3) == 1.0


def test_all_cites_at_k_needs_every_cite() -> None:
    ranked = ["a", "b", "c", "d", "e"]
    assert all_cites_at_k(ranked, ["b", "e"], 3) is False
    assert all_cites_at_k(ranked, ["b", "e"], 5) is True
