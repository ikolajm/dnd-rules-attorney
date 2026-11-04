"""Tests for the agentic search loop, against a scripted backend."""

from collections.abc import Mapping
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from rules_attorney.agentic import (
    INVALID_CALL,
    Call,
    Reply,
    ToolCall,
    Trace,
    Turn,
    build_dispatch,
    hand_over,
    loop_handed,
    run_loop,
)
from rules_attorney.corpus import Entry
from rules_attorney.retrieve import NOMIC


class FakeBackend:
    """Returns scripted replies in order and records what it is told."""

    def __init__(self, replies: list[Reply]) -> None:
        self.replies = replies
        self.told: list[list[str]] = []

    def ask(self) -> Reply:
        return self.replies.pop(0)

    def tell(self, results: list[str]) -> None:
        self.told.append(results)


def dispatch(name: str, arguments: Mapping[str, object]) -> list[str]:
    """Eight paths for any call, so a search's cut to five shows."""
    return [f"{name}-{n}" for n in range(8)]


BY_PATH = {
    f"{tool}-{n}": Entry(f"{tool}-{n}", "text")
    for tool in ("search", "lookup")
    for n in range(8)
}


def search_call() -> ToolCall:
    return ToolCall("search", {"query": "q"})


def test_a_reply_without_calls_is_done() -> None:
    backend = FakeBackend([Reply([], 0, 0)])
    trace = run_loop(backend, dispatch, BY_PATH)
    assert trace.stopped == "done"
    assert len(trace.turns) == 1
    assert backend.told == []


def test_calls_past_the_cap_never_run() -> None:
    # The cap of six falls inside the second turn, after its second call.
    four = [search_call() for _ in range(4)]
    backend = FakeBackend([Reply(four, 0, 0), Reply(four, 0, 0)])
    trace = run_loop(backend, dispatch, BY_PATH)
    assert trace.stopped == "cap"
    assert sum(len(turn.calls) for turn in trace.turns) == 6
    # Only the first turn is answered; nothing is told past the cap.
    assert [len(results) for results in backend.told] == [4]


def test_an_invalid_call_is_told_and_counts() -> None:
    # The lookup's argument sent to search, which leaves query missing.
    invalid = ToolCall("search", {"name": "x"})
    backend = FakeBackend([Reply([invalid], 0, 0), Reply([], 0, 0)])
    trace = run_loop(backend, dispatch, BY_PATH)
    call = trace.turns[0].calls[0]
    assert not call.valid
    assert call.ranking == []
    assert backend.told == [[INVALID_CALL]]
    capped = run_loop(FakeBackend([Reply([invalid], 0, 0)]), dispatch, BY_PATH, cap=1)
    assert capped.stopped == "cap"


def test_a_search_is_shown_five_and_kept_whole() -> None:
    backend = FakeBackend([Reply([search_call()], 0, 0), Reply([], 0, 0)])
    trace = run_loop(backend, dispatch, BY_PATH)
    told = backend.told[0][0]
    assert "## search-4" in told
    assert "## search-5" not in told
    assert len(trace.turns[0].calls[0].ranking) == 8


def test_hand_over_puts_lookups_first_and_fills_ten() -> None:
    # A loop that never searched still hands over ten, from the question's.
    lookup = Call("lookup", {"name": "x"}, True, ["L"])
    trace = Trace([Turn([lookup], 0.0, 0, 0)], "done")
    question = [f"q{n}" for n in range(12)]
    assert hand_over(trace, question) == ["L"] + [f"q{n}" for n in range(9)]


def fake_embed(texts: list[str]) -> NDArray[np.float64]:
    """One fixed vector for any query, so the ranking rests on the matrix alone."""
    return np.array([[1.0, 0.0]])


def test_dispatch_routes_a_search_whole_and_a_lookup_to_the_index() -> None:
    # Seven rows whose cosine against [1, 0] rises with n, more than a search
    # shows, so a cut to five would show.
    matrix = np.array([[float(n), 1.0] for n in range(7)])
    paths = [f"p{n}" for n in range(7)]
    index = {"fireball": ["spells > fireball"]}
    routed = build_dispatch(NOMIC, fake_embed, matrix, paths, index)
    assert routed("search", {"query": "q"}) == [f"p{n}" for n in range(6, -1, -1)]
    assert routed("lookup", {"name": "Fireball"}) == ["spells > fireball"]


def record(item_id: str, **config: object) -> dict[str, Any]:
    """A loop record from a clean dev run of m, any config field overridden."""
    base: dict[str, object] = {
        "split": "dev",
        "model": "m",
        "dirty": False,
        "commit": "abc",
    }
    return {"id": item_id, "handed": ["p"], "config": base | config}


def test_loop_handed_maps_each_id_to_its_ten() -> None:
    records = [record("a"), record("b")]
    assert loop_handed(records, "dev", "m", ["a", "b"]) == {"a": ["p"], "b": ["p"]}


def test_loop_handed_refuses_another_split() -> None:
    with pytest.raises(ValueError, match="split"):
        loop_handed([record("a", split="test")], "dev", "m", ["a"])


def test_loop_handed_refuses_another_model() -> None:
    # The loop's model is the answering model, as level 3's planner is.
    with pytest.raises(ValueError, match="from m"):
        loop_handed([record("a", model="other")], "dev", "m", ["a"])


def test_loop_handed_refuses_a_dirty_tree() -> None:
    with pytest.raises(ValueError, match="dirty"):
        loop_handed([record("a", dirty=True)], "dev", "m", ["a"])


def test_loop_handed_refuses_two_commits() -> None:
    records = [record("a"), record("b", commit="def")]
    with pytest.raises(ValueError, match="commit"):
        loop_handed(records, "dev", "m", ["a", "b"])


def test_loop_handed_refuses_a_missing_item() -> None:
    with pytest.raises(ValueError, match="miss"):
        loop_handed([record("a")], "dev", "m", ["a", "b"])
