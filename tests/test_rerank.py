"""Tests for reordering entries by a cross-encoder's scores."""

import pytest

from rules_attorney.corpus import Entry
from rules_attorney.rerank import (
    Score,
    TruncationError,
    fused_order,
    refuse_truncation,
    rerank,
)

# Its words appear in no entry text, so a pair can only carry it because
# rerank put it there.
QUESTION = "Can a prone creature stand up as a bonus action?"


def by_length(pairs: list[tuple[str, str]]) -> list[float]:
    """A fake score: each pair's text length, so longer text ranks higher."""
    return [float(len(text)) for _, text in pairs]


def recording(sent: list[list[tuple[str, str]]]) -> Score:
    """A fake score that keeps every batch of pairs it is sent and ties them all."""

    def fake(pairs: list[tuple[str, str]]) -> list[float]:
        sent.append(pairs)
        return [1.0 for _ in pairs]

    return fake


def test_paths_come_back_best_score_first() -> None:
    entries = [
        Entry(path="short", text="a"),
        Entry(path="long", text="aaa"),
        Entry(path="mid", text="aa"),
    ]
    assert rerank(QUESTION, entries, by_length) == ["long", "mid", "short"]


def test_each_pair_puts_the_question_first() -> None:
    # A cross-encoder reads its input in order and was trained with the
    # query in front, so a swapped pair scores without failing.
    sent: list[list[tuple[str, str]]] = []
    entries = [Entry(path="a", text="first"), Entry(path="b", text="second")]
    rerank(QUESTION, entries, recording(sent))
    assert sent == [[(QUESTION, "first"), (QUESTION, "second")]]


def test_a_tie_keeps_the_order_given() -> None:
    # An argsort reversed, the pattern in retrieve.rank, would flip tied
    # entries while ordering every distinct score correctly.
    entries = [
        Entry(path="first", text="x"),
        Entry(path="second", text="x"),
        Entry(path="third", text="x"),
    ]
    assert rerank(QUESTION, entries, recording([])) == ["first", "second", "third"]


def test_a_pair_at_the_limit_passes() -> None:
    # The longest is exactly the limit, which the window holds whole. The
    # test fails only if this raises.
    refuse_truncation([3, 5], limit=5)


def test_a_pair_past_the_limit_is_refused() -> None:
    # Not the first length, so a check of only one pair would miss it.
    with pytest.raises(TruncationError):
        refuse_truncation([3, 6, 4], limit=5)


def test_fused_order_is_neither_order_alone() -> None:
    # p is second and first, 1/62 + 1/61; r first and third, 1/61 + 1/63;
    # q third and second, 1/63 + 1/62. Highest first, that is p, r, q.
    assert fused_order(["r", "p", "q"], ["p", "q", "r"]) == ["p", "r", "q"]


def test_fused_order_breaks_a_tie_by_the_reranked_order() -> None:
    # Each is first in one order and second in the other, so they tie, and
    # the first ranking handed to fuse decides. Swapped, the row measured on
    # dev would not be the one this code produces.
    assert fused_order(["b", "a"], ["a", "b"]) == ["b", "a"]
