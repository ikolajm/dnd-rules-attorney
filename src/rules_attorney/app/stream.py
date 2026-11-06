"""The served pipeline, from one question to the events the frontend renders."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from rules_attorney.answer import build_prompt, parse_reply
from rules_attorney.corpus import Entry
from rules_attorney.gate import build_gate_prompt, parse_gate
from rules_attorney.multihop import build_plan_prompt, merged_ranking, parse_plan
from rules_attorney.retrieve import NOMIC, Embed, embed_query, rank

# The whole run's limit, in seconds. On level 3's dev run the slowest ruling
# that parsed took 9.4 seconds and the one that looped to its cap took 44.8.
LIMIT = 30.0
# The entries handed to the answer, as scripts/answer_dev.py hands them.
K = 10

# A model call, from a prompt to its raw reply.
type Call = Callable[[str], Awaitable[str]]


@dataclass(frozen=True)
class Calls:
    """The model calls a run makes: Ollama's when served, fakes in a test."""

    gate: Call
    plan: Call
    answer: Call
    embed: Embed


@dataclass(frozen=True)
class Event:
    """One server-sent event: its name and its JSON."""

    name: str
    data: dict[str, Any]


def error(reason: str) -> Event:
    """The error event naming the stage that failed."""
    return Event("error", {"reason": reason})


async def run(
    question: str,
    calls: Calls,
    entries: list[Entry],
    matrix: NDArray[np.float64],
    limit: float = LIMIT,
) -> AsyncIterator[Event]:
    """The run's events in order, ending at a refusal, a ruling or an error."""
    deadline = asyncio.get_running_loop().time() + limit
    paths = [entry.path for entry in entries]
    by_path = {entry.path: entry for entry in entries}

    try:
        # Each timeout holds an await and never a yield. One spanning a yield
        # would fire while the generator is paused, in its caller's code.
        async with asyncio.timeout_at(deadline):
            gate_reply = await calls.gate(build_gate_prompt(question))
        # A reply that fails to parse passes, since unsure passes.
        about_rules = parse_gate(gate_reply) is not False
        yield Event("gate", {"about_rules": about_rules})
        if not about_rules:
            return

        async with asyncio.timeout_at(deadline):
            plan_reply = await calls.plan(build_plan_prompt(question))
        # A plan that fails to parse goes on with no sub-questions, as the
        # measured level 3 run does.
        sub_questions = parse_plan(plan_reply) or []
        yield Event("plan", {"sub_questions": sub_questions})

        rankings: list[list[str]] = []
        async with asyncio.timeout_at(deadline):
            for text in [question, *sub_questions]:
                # embed_query blocks, so it runs on a worker thread.
                vector = await asyncio.to_thread(embed_query, text, NOMIC, calls.embed)
                rankings.append(rank(vector, matrix, paths))
        top = merged_ranking(rankings[0], rankings[1:])[:K]
        handed = [by_path[path] for path in top]
        yield Event(
            "entries",
            {"entries": [{"path": entry.path, "text": entry.text} for entry in handed]},
        )

        async with asyncio.timeout_at(deadline):
            reply = await calls.answer(build_prompt(question, handed))
        ruling = parse_reply(reply)
        if ruling is None:
            yield error("ruling-unparsed")
            return
        yield Event("ruling", ruling.model_dump())

    # Both Ollama clients raise ConnectionError when the server is down. A
    # stop raises neither: it cancels the task, and CancelledError passes.
    except ConnectionError:
        yield error("unreachable")
    except TimeoutError:
        yield error("timeout")
