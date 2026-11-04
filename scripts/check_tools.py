"""Checks that a model calls a declared tool with valid arguments.

The entry gate for the agentic loop's rows, as check_key_order.py is the
ladder's. Each of the first dev items is sent as the loop's first turn, and
the model must make at least one call naming a declared tool with arguments
that validate against its model. Exits non-zero if any item has none.

Calls the live Ollama server, or the Claude API for a model named claude-.
"""

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from anthropic.types import MessageParam, ToolUseBlock

from rules_attorney.agentic import build_loop_prompt, ollama_turn
from rules_attorney.hosted import MODEL_PREFIX, claude_turn
from rules_attorney.tools import valid_call

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "gold" / "gold.json"


def first_calls(question: str, model: str) -> list[tuple[str, Mapping[str, object]]]:
    """The tool calls in the model's first turn on the question, a live call."""
    prompt = build_loop_prompt(question)
    if model.startswith(MODEL_PREFIX):
        messages: list[MessageParam] = [{"role": "user", "content": prompt}]
        message = claude_turn(messages, model)
        return [
            (block.name, block.input)
            for block in message.content
            if isinstance(block, ToolUseBlock)
        ]
    reply = ollama_turn([{"role": "user", "content": prompt}], model)
    return [
        (call.function.name, call.function.arguments) for call in reply.tool_calls or []
    ]


def main() -> None:
    """Check the model's first turn on each item and exit non-zero on a miss."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model")
    parser.add_argument("--items", type=int, default=5)
    args = parser.parse_args()
    items: list[dict[str, Any]] = json.loads(GOLD.read_text(encoding="utf-8"))
    chosen = [item for item in items if item["split"] == "dev"][: args.items]
    missed = 0
    for item in chosen:
        calls = first_calls(item["question"], args.model)
        if not calls:
            print(f"{item['id']}: no tool call")
        valid = any(valid_call(name, arguments) for name, arguments in calls)
        if not valid:
            missed += 1
        for name, arguments in calls:
            status = "ok" if valid_call(name, arguments) else "INVALID"
            print(f"{item['id']}: {name} {dict(arguments)} {status}")
    print(f"valid calls: {len(chosen) - missed} / {len(chosen)}")
    if missed:
        sys.exit(1)


if __name__ == "__main__":
    main()
