"""Tests for the agentic search loop, against a scripted backend."""

from collections.abc import Mapping

from rules_attorney.agentic import (
    INVALID_CALL,
    Call,
    Reply,
    ToolCall,
    Trace,
    Turn,
    hand_over,
    run_loop,
)
from rules_attorney.corpus import Entry


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
