"""Tests for BM25 keyword retrieval."""

import bm25s
import pytest

from rules_attorney.bm25 import (
    bm25_rank,
    build_index,
    idf,
    scores,
    term_score,
    tokenize,
)

# A word repeated within one entry, so counting occurrences in place of
# entries gives a different IDF than the reference does.
TEXTS = [
    "The grappled creature can't move.",
    "Shove a creature to knock it prone or push it away.",
    "A prone creature has disadvantage on attack rolls. Prone prone.",
    "Two-handed weapons need two hands.",
]
QUESTIONS = ["prone creature", "shove two hands", "prone prone grappled"]


def test_tokenize_folds_case_and_punctuation() -> None:
    assert tokenize("Shove! Two-handed") == ["shove", "two", "handed"]


def test_idf_never_negative() -> None:
    assert idf(10, 10) >= 0.0


def test_term_score_saturates() -> None:
    assert term_score(10, 10, 10.0, 1.0) < 10 * term_score(1, 10, 10.0, 1.0)


def test_term_score_favors_short_entries() -> None:
    assert term_score(1, 5, 10.0, 1.0) > term_score(1, 20, 10.0, 1.0)


def test_rare_word_outranks_common_word() -> None:
    index = build_index(
        ["common-x", "common-y", "rare"], ["banana x", "banana y", "apple z"]
    )
    assert bm25_rank(index, "apple banana")[0] == "rare"


def test_unknown_words_score_zero() -> None:
    index = build_index(["first", "second"], ["grappled creature", "prone creature"])
    assert scores(index, "fireball dragon") == [0.0, 0.0]


def test_scores_match_the_reference() -> None:
    index = build_index(["a", "b", "c", "d"], TEXTS)
    # Literal parameters, never this module's K1 and B, so a change to
    # either moves one side only.
    reference = bm25s.BM25(method="lucene", k1=1.2, b=0.75)
    reference.index([tokenize(text) for text in TEXTS], show_progress=False)
    for question in QUESTIONS:
        expected = list(reference.get_scores(tokenize(question)))
        assert scores(index, question) == pytest.approx(expected)
