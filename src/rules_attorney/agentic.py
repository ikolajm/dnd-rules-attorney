"""The agentic search loop, from a dispute to the entries it hands over."""

from typing import Any

import ollama

from rules_attorney.answer import OPTIONS, THINK
from rules_attorney.tools import ollama_tools

# Sent word for word to both rows, as the first message of every loop.
LOOP_INSTRUCTIONS = (
    "Find the rules entries the dispute below turns on. Use search to find a "
    "rule by what it says, and lookup to fetch a record by its name. Read what "
    "each call returns, and when an entry points to another rule, search for "
    "that rule too. Do not rule on the dispute. When you have every entry the "
    "ruling needs, reply without calling a tool."
)


def build_loop_prompt(question: str) -> str:
    """The loop's instructions, then the question."""
    parts = [LOOP_INSTRUCTIONS, f"Question: {question}"]
    return "\n\n".join(parts)


def ollama_turn(messages: list[dict[str, Any]], model: str) -> ollama.Message:
    """The model's next turn in the loop, with the tools and no format."""
    response = ollama.chat(
        model=model,
        messages=messages,
        tools=ollama_tools(),
        think=THINK,
        options=OPTIONS,
    )
    return response.message
