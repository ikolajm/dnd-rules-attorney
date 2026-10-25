"""Tests for the judge."""

from rules_attorney.judge import flag_correct


def test_flag_correct_misses_a_contested_item_left_unflagged() -> None:
    assert not flag_correct("contested", False)


def test_flag_correct_refuses_a_settled_item_flagged() -> None:
    assert not flag_correct("settled", True)


def test_flag_correct_expects_a_rules_as_intended_item_flagged() -> None:
    # Its text alone does not settle it, so it is flagged like a contested one.
    assert flag_correct("rules-as-intended", True)
