"""The hosted answering step, the ceiling row answered through the Claude API."""

from typing import Any, Final

import anthropic
from anthropic.types import Message

from rules_attorney.answer import Ruling

MODEL_PREFIX = "claude-"
# Opus 5.5 defaults to medium. Its thinking cannot be turned off, so effort
# is the only control over how hard it reasons. Final keeps its type the
# literal "high", which the SDK's effort parameter takes; a plain str fails.
EFFORT: Final = "high"
# Thinking counts against this cap as well as the ruling.
MAX_TOKENS = 16000


def enum_consts(value: Any) -> Any:
    """A copy of a JSON value with every const written as a one-value enum."""
    if isinstance(value, dict):
        copy = {key: enum_consts(item) for key, item in value.items()}
        if "const" in copy:
            copy["enum"] = [copy.pop("const")]
        return copy
    if isinstance(value, list):
        return [enum_consts(item) for item in value]
    return value


# The SDK's rewrite moves a const into the description, where the grammar
# does not enforce it, and keeps an enum. Each kind is a one-value Literal,
# which pydantic writes as a const.
RULING_SCHEMA = anthropic.transform_schema(enum_consts(Ruling.model_json_schema()))


def claude_answer(prompt: str, *, model: str) -> Message:
    """The model's raw response to the prompt, a live call."""
    client = anthropic.Anthropic()
    # No thinking parameter: Opus 5.5 runs adaptive without one and refuses
    # disabled. No temperature or seed, which it refuses too.
    return client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        output_config={
            "effort": EFFORT,
            "format": {"type": "json_schema", "schema": RULING_SCHEMA},
        },
        messages=[{"role": "user", "content": prompt}],
    )
