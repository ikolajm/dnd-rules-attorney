"""Tests for scoring retrieval against gold cites."""

from rules_attorney.metrics import all_cites_at_k, recall_at_k


def test_recall_at_k_counts_the_share_of_cites() -> None:
    ranked: list[tuple[str, ...]] = [("a",), ("b",), ("c",), ("d",), ("e",)]
    assert recall_at_k(ranked, ["b", "e"], 3) == 0.5


def test_recall_at_k_stops_at_k() -> None:
    ranked: list[tuple[str, ...]] = [("a",), ("b",), ("c",)]
    assert recall_at_k(ranked, ["c"], 2) == 0.0
    assert recall_at_k(ranked, ["c"], 3) == 1.0


def test_all_cites_at_k_needs_every_cite() -> None:
    ranked: list[tuple[str, ...]] = [("a",), ("b",), ("c",), ("d",), ("e",)]
    assert all_cites_at_k(ranked, ["b", "e"], 3) is False
    assert all_cites_at_k(ranked, ["b", "e"], 5) is True


def test_one_chunk_can_hold_every_cite() -> None:
    # k counts chunks, not paths: one chunk covering both cites finds
    # both at k of 1. The second chunk makes k of 1 leave something out.
    ranked = [("a", "b"), ("c",)]
    assert recall_at_k(ranked, ["a", "b"], 1) == 1.0
    assert all_cites_at_k(ranked, ["a", "b"], 1) is True
