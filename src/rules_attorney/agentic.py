"""The agentic search loop, from a dispute to the entries it hands over."""

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import numpy as np
import ollama
from numpy.typing import NDArray

from rules_attorney.answer import OPTIONS, THINK
from rules_attorney.corpus import Entry
from rules_attorney.fusion import fuse
from rules_attorney.lookup import lookup_order
from rules_attorney.retrieve import Embed, Embedder
from rules_attorney.tools import (
    SEARCH_K,
    LookupArgs,
    SearchArgs,
    lookup,
    ollama_tools,
    render_result,
    search,
    valid_call,
)

# Sent word for word to both rows, as the first message of every loop.
LOOP_INSTRUCTIONS = (
    "Find the rules entries the dispute below turns on. Use search to find a "
    "rule by what it says, and lookup to fetch a record by its name. Read what "
    "each call returns, and when an entry points to another rule, search for "
    "that rule too. Do not rule on the dispute. When you have every entry the "
    "ruling needs, reply without calling a tool."
)
# The most tool calls one item's loop makes, across all its turns. A starting
# value, not tuned; the answer run reports how many items reach it.
CALL_CAP = 6
# Sent in place of a result when a call's arguments do not validate, so the
# model can try again. The call still counts toward the cap.
INVALID_CALL = "That call does not match the tool's arguments."


@dataclass(frozen=True)
class ToolCall:
    """One tool call as a backend reports it."""

    name: str
    arguments: Mapping[str, object]


@dataclass(frozen=True)
class Reply:
    """One turn of the model's, its calls and token counts."""

    calls: list[ToolCall]
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class Call:
    """One call as the loop ran it, and every path it returned."""

    name: str
    arguments: Mapping[str, object]
    valid: bool
    ranking: list[str]


@dataclass(frozen=True)
class Turn:
    """One turn as the loop ran it."""

    calls: list[Call]
    seconds: float
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class Trace:
    """Every turn of one item's loop, and why it stopped."""

    turns: list[Turn]
    stopped: Literal["done", "cap"]


class Backend(Protocol):
    """A model's side of the loop, holding its own conversation."""

    def ask(self) -> Reply:
        """The model's next turn."""
        ...

    def tell(self, results: list[str]) -> None:
        """One result per call of the last turn, in its order."""
        ...


# A tool's name and arguments to the paths it returns: a lookup's every path,
# a search's whole ranking.
type Dispatch = Callable[[str, Mapping[str, object]], list[str]]


def run_loop(
    backend: Backend,
    dispatch: Dispatch,
    by_path: dict[str, Entry],
    cap: int = CALL_CAP,
) -> Trace:
    """Turns until the model stops calling tools or the calls reach the cap."""
    turns: list[Turn] = []
    made = 0
    while True:
        # Only the model's turn is timed; the item's searches are timed with it.
        start = time.perf_counter()
        reply = backend.ask()
        seconds = time.perf_counter() - start
        calls: list[Call] = []
        results: list[str] = []
        for tool_call in reply.calls:
            if made == cap:
                break
            made += 1
            if not valid_call(tool_call.name, tool_call.arguments):
                calls.append(Call(tool_call.name, tool_call.arguments, False, []))
                results.append(INVALID_CALL)
                continue
            ranking = dispatch(tool_call.name, tool_call.arguments)
            # The model reads a search's first few and a lookup's every path;
            # the whole ranking is kept for the hand-over's fusion.
            shown = ranking[:SEARCH_K] if tool_call.name == "search" else ranking
            calls.append(Call(tool_call.name, tool_call.arguments, True, ranking))
            results.append(render_result(shown, by_path))
        turns.append(Turn(calls, seconds, reply.input_tokens, reply.output_tokens))
        if not reply.calls:
            return Trace(turns, "done")
        # Ends before tell, so no call waits on a result past the cap.
        if made == cap:
            return Trace(turns, "cap")
        backend.tell(results)


def hand_over(trace: Trace, question_ranking: list[str], k: int = 10) -> list[str]:
    """Lookups first, then the question's and searches' rankings fused, cut to k."""
    calls = [call for turn in trace.turns for call in turn.calls if call.valid]
    linked = [path for call in calls if call.name == "lookup" for path in call.ranking]
    rankings = [question_ranking] + [
        call.ranking for call in calls if call.name == "search"
    ]
    return lookup_order(linked, fuse(rankings), k)


def build_dispatch(
    embedder: Embedder,
    embed: Embed,
    matrix: NDArray[np.float64],
    paths: list[str],
    index: dict[str, list[str]],
) -> Dispatch:
    """Loop's dispatch over the corpus: a search's whole ranking, a lookup's paths."""

    def dispatch(name: str, arguments: Mapping[str, object]) -> list[str]:
        if name == "search":
            query = SearchArgs.model_validate(arguments).query
            return search(
                query,
                embedder=embedder,
                embed=embed,
                matrix=matrix,
                paths=paths,
                k=len(paths),
            )
        return lookup(LookupArgs.model_validate(arguments).name, index)

    return dispatch


def build_loop_prompt(question: str) -> str:
    """The loop's instructions, then the question."""
    parts = [LOOP_INSTRUCTIONS, f"Question: {question}"]
    return "\n\n".join(parts)


def ollama_turn(
    messages: Sequence[Mapping[str, Any] | ollama.Message], model: str
) -> ollama.ChatResponse:
    """The model's next turn in the loop, with its token counts."""
    response = ollama.chat(
        model=model,
        messages=messages,
        tools=ollama_tools(),
        think=THINK,
        options=OPTIONS,
    )
    return response


class OllamaBackend:
    """The loop's conversation with a model through Ollama."""

    def __init__(self, question: str, model: str) -> None:
        self.model = model
        self.messages: list[Mapping[str, Any] | ollama.Message] = [
            {"role": "user", "content": build_loop_prompt(question)}
        ]
        # The last turn's tool names, which each result is sent under.
        self.names: list[str] = []

    def ask(self) -> Reply:
        """The model's next turn, kept in the conversation."""
        response = ollama_turn(self.messages, self.model)
        self.messages.append(response.message)
        calls = [
            ToolCall(call.function.name, call.function.arguments)
            for call in response.message.tool_calls or []
        ]
        self.names = [call.name for call in calls]
        return Reply(calls, response.prompt_eval_count or 0, response.eval_count or 0)

    def tell(self, results: list[str]) -> None:
        """Each result as a tool message, under its call's tool name."""
        for name, result in zip(self.names, results, strict=True):
            self.messages.append({"role": "tool", "tool_name": name, "content": result})


def loop_handed(
    records: list[dict[str, Any]], split: str, model: str, ids: list[str]
) -> dict[str, list[str]]:
    """Each item's id to the ten its loop record handed over, refusing a mismatch."""
    configs = [record["config"] for record in records]
    if any(config["split"] != split for config in configs):
        raise ValueError(f"loop records are not all from the {split} split")
    if any(config["model"] != model for config in configs):
        raise ValueError(f"loop records are not all from {model}")
    if any(config["dirty"] for config in configs):
        raise ValueError("loop records come from a dirty tree")
    if len({config["commit"] for config in configs}) > 1:
        raise ValueError("loop records span more than one commit")
    handed = {record["id"]: record["handed"] for record in records}
    missing = [item_id for item_id in ids if item_id not in handed]
    if missing:
        raise ValueError(f"loop records miss {len(missing)} items, {missing[0]} first")
    return handed
