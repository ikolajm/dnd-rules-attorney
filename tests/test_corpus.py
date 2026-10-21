"""Tests for building the citable corpus."""

import pytest

from rules_attorney.corpus import slug


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("Verbal (V)", "verbal-v"),
        ("Variant: Encumbrance", "variant-encumbrance"),
        ("What Is a Spell?", "what-is-a-spell"),
        ("Climbing, Swimming, and Crawling", "climbing-swimming-and-crawling"),
        ("Two-Weapon Fighting", "two-weapon-fighting"),
    ],
)
def test_slug(given: str, expected: str) -> None:
    assert slug(given) == expected
