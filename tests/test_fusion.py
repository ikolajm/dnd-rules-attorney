"""Tests for fusing rankings by reciprocal rank."""

import pytest

from rules_attorney.fusion import fuse, fused_scores


def test_a_label_first_in_both_scores_two_over_sixty_one() -> None:
    # Pinned as a value: a rank counted from 0 would score 2/60 and leave
    # most orderings as they were.
    scores = fused_scores([["a", "b"], ["a", "b"]])
    assert scores["a"] == pytest.approx(2 / 61)


def test_the_constant_is_the_one_given() -> None:
    assert fused_scores([["a"]], constant=0)["a"] == pytest.approx(1.0)


def test_a_label_in_one_ranking_scores_from_that_one() -> None:
    scores = fused_scores([["a"], ["b"]])
    assert scores == pytest.approx({"a": 1 / 61, "b": 1 / 61})


def test_second_in_both_beats_first_in_one_and_last_in_the_other() -> None:
    # The point of fusing: agreement outranks one ranking's favourite
    # that the other buries.
    semantic = ["favourite", "agreed", "c", "d", "buried"]
    keyword = ["buried", "agreed", "c", "d", "favourite"]
    assert fuse([semantic, keyword])[0] == "agreed"


def test_a_tie_keeps_the_first_ranking_order() -> None:
    assert fuse([["a", "b"], ["b", "a"]]) == ["a", "b"]
