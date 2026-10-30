"""Tests for the served pipeline, driven with fake model calls."""

import asyncio
import contextlib

import numpy as np
from numpy.typing import NDArray

from rules_attorney.corpus import Entry
from rules_attorney.stream import Call, Calls, Event, run

QUESTION = "Can a grappled creature still attack?"
ENTRIES = [
    Entry("conditions > grappled", "A grappled creature's speed becomes 0."),
    Entry("actions-in-combat > attack", "You make one melee or ranged attack."),
]
MATRIX = np.array([[1.0, 0.0], [0.0, 1.0]])

GATE_PASS = '{"about_rules": true}'
GATE_REFUSE = '{"about_rules": false}'
PLAN = '{"sub_questions": ["What does the grappled condition do?"]}'
RULING = (
    '{"explanation": "Grappled only sets speed to 0.", "ambiguous": false, '
    '"answer": {"kind": "yes-or-no", "verdict": "yes"}, '
    '"cites": ["conditions > grappled"]}'
)


def embed(texts: list[str]) -> NDArray[np.float64]:
    """A fixed vector per text, so every ranking is the same."""
    return np.ones((len(texts), 2))


def reply(text: str) -> Call:
    """A fake model call that answers every prompt with the text given."""

    async def call(prompt: str) -> str:
        return text

    return call


PASSING = reply(GATE_PASS)
PLANNING = reply(PLAN)
RULING_CALL = reply(RULING)


def calls(
    gate: Call = PASSING, plan: Call = PLANNING, answer: Call = RULING_CALL
) -> Calls:
    """Fake calls that rule, with any of them swapped."""
    return Calls(gate=gate, plan=plan, answer=answer, embed=embed)


def collect(fakes: Calls) -> list[Event]:
    """Every event of one run, in order."""

    async def gather() -> list[Event]:
        return [event async for event in run(QUESTION, fakes, ENTRIES, MATRIX)]

    return asyncio.run(gather())


def names(events: list[Event]) -> list[str]:
    return [event.name for event in events]


def test_a_refusal_ends_after_the_gate() -> None:
    events = collect(calls(gate=reply(GATE_REFUSE)))
    assert names(events) == ["gate"]
    assert events[0].data == {"about_rules": False}


def test_a_failed_plan_still_rules() -> None:
    events = collect(calls(plan=reply("")))
    assert names(events) == ["gate", "plan", "entries", "ruling"]
    assert events[1].data == {"sub_questions": []}


def test_a_failed_ruling_ends_in_ruling_unparsed() -> None:
    events = collect(calls(answer=reply("")))
    assert events[-1] == Event("error", {"reason": "ruling-unparsed"})


def test_an_unreachable_model_ends_in_unreachable() -> None:
    async def down(prompt: str) -> str:
        # The message Ollama's client raises when its server is not running.
        raise ConnectionError("Failed to connect to Ollama.")

    events = collect(calls(gate=down))
    assert events == [Event("error", {"reason": "unreachable"})]


def test_a_call_past_the_limit_ends_in_timeout() -> None:
    cancelled: list[bool] = []

    async def slow(prompt: str) -> str:
        try:
            await asyncio.sleep(2)
        except asyncio.CancelledError:
            cancelled.append(True)
            raise
        return RULING

    async def run_past_the_limit() -> list[Event]:
        fakes = calls(answer=slow)
        events = [event async for event in run(QUESTION, fakes, ENTRIES, MATRIX, 0.5)]
        # Checked before asyncio.run exits, since its shutdown cancels any
        # task still pending, a call the limit failed to reach among them.
        assert cancelled == [True]
        return events

    events = asyncio.run(run_past_the_limit())
    assert events[-1] == Event("error", {"reason": "timeout"})


def test_a_stop_cancels_the_call_in_flight() -> None:
    cancelled: list[bool] = []

    async def stop_mid_ruling() -> None:
        started = asyncio.Event()

        async def hang(prompt: str) -> str:
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.append(True)
                raise
            return RULING

        async def consume() -> None:
            async for _ in run(QUESTION, calls(answer=hang), ENTRIES, MATRIX):
                pass

        task = asyncio.create_task(consume())
        await started.wait()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        # Checked before asyncio.run exits, since its shutdown cancels any
        # task still pending, a call a stop failed to reach among them.
        assert cancelled == [True]

    asyncio.run(stop_mid_ruling())
