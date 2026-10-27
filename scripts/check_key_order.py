"""Checks that each model named on the command line keeps a schema's key order.

The entry gate for a model. The ruling's fields are ordered so the model
reasons and flags before it rules, and Ollama re-sorts a schema's keys
alphabetically for a model with neither a renderer nor a Go template
(ollama/ollama#18717), so the grammar forces the sorted order. Each model is
sent the same three keys in two orders, neither of them alphabetical in the
same direction, and must write both back in the order given. Exits non-zero
if any model does not.

Calls the live Ollama server.
"""

import json
import sys
from typing import Any

import ollama

from rules_attorney.answer import NUM_CTX, PENALTIES, SEED, TEMPERATURE, THINK

KEYS = ["zulu", "mike", "alpha"]
PROMPT = (
    "Reply with a JSON object. zulu is a color, mike is an animal, alpha is a number."
)


def schema(order: list[str]) -> dict[str, Any]:
    """An object schema of string fields, all required, in the order given."""
    return {
        "type": "object",
        "properties": {key: {"type": "string"} for key in order},
        "required": order,
    }


def written_order(reply: str) -> list[str] | None:
    """The reply's keys in the order written, None when it is not a JSON object."""
    try:
        value = json.loads(reply)
    except json.JSONDecodeError:
        return None
    return list(value) if isinstance(value, dict) else None


def main() -> None:
    """Check each model and exit non-zero if any reorders the keys."""
    failed = []
    for model in sys.argv[1:]:
        for order in (KEYS, KEYS[::-1]):
            reply = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": PROMPT}],
                format=schema(order),
                think=THINK,
                options={
                    "temperature": TEMPERATURE,
                    "seed": SEED,
                    "num_ctx": NUM_CTX,
                    "num_predict": 200,
                    **PENALTIES,
                },
            ).message.content
            written = written_order(reply or "")
            kept = written == order
            print(
                f"{model}: schema {order} -> reply {written} {'ok' if kept else 'FAIL'}"
            )
            if not kept:
                failed.append(model)

    if failed:
        print(f"key order not kept: {sorted(set(failed))}")
        sys.exit(1)


if __name__ == "__main__":
    main()
