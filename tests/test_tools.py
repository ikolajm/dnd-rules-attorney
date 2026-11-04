"""Tests for the tools the loop's model calls."""

import numpy as np
from numpy.typing import NDArray

from rules_attorney.retrieve import NOMIC
from rules_attorney.tools import (
    NO_RECORD,
    lookup,
    render_result,
    search,
    valid_call,
)

# Written by hand in the shape name_index builds, so no corpus is loaded.
INDEX = {"fireball": ["spells > fireball"], "dagger": ["equipment > dagger"]}


def test_lookup_ignores_case_and_surrounding_spaces() -> None:
    assert lookup("  Fireball ", INDEX) == ["spells > fireball"]


def test_lookup_resolves_a_plural() -> None:
    assert lookup("Daggers", INDEX) == ["equipment > dagger"]


def test_an_unresolved_name_returns_nothing_and_says_so() -> None:
    # The match is exact, so a near miss resolves to nothing rather than a guess.
    assert lookup("Fire Ball", INDEX) == []
    assert render_result([], {}) == NO_RECORD


def fake_embed(texts: list[str]) -> NDArray[np.float64]:
    """One fixed vector for any query, so the ranking rests on the matrix alone."""
    return np.array([[1.0, 0.0]])


def test_search_returns_k_paths_in_rank_order() -> None:
    # Unit rows scoring 0, 1 and 0.6 by cosine against the query's [1, 0].
    matrix = np.array([[0.0, 1.0], [1.0, 0.0], [0.6, 0.8]])
    paths = ["a", "b", "c"]
    found = search(
        "q", embedder=NOMIC, embed=fake_embed, matrix=matrix, paths=paths, k=2
    )
    assert found == ["b", "c"]


def test_valid_call_refuses_an_unknown_tool() -> None:
    assert not valid_call("fetch", {"name": "Fireball"})


def test_valid_call_refuses_a_missing_argument() -> None:
    # The lookup's argument sent to search, which leaves query missing.
    assert not valid_call("search", {"name": "Fireball"})


def test_valid_call_accepts_a_declared_call() -> None:
    assert valid_call("lookup", {"name": "Fireball"})
