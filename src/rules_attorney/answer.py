"""The answering step, from retrieved entries to a validated ruling."""

import ollama
from pydantic import BaseModel, ValidationError

from rules_attorney.corpus import Entry, render_markdown

MODEL = "qwen3.5:9b"
SEED = 1
TEMPERATURE = 0.0
THINK = False
NUM_CTX = 16384

INSTRUCTIONS = (
    "Rule on the dispute below using only the rules entries given, and nothing "
    "else. Cite each entry your ruling rests on by its path, written exactly as "
    "it appears after ##. In the explanation, give the rule, the fact from the "
    "question it applies to, and the conclusion. Where the entries do not settle "
    "the question, set ambiguous to true, give each reading, and say why the text "
    "does not decide between them."
)


class Ruling(BaseModel):
    """The ruling a model returns."""

    verdict: str
    explanation: str
    ambiguous: bool
    cites: list[str]


def parse_reply(content: str) -> Ruling | None:
    """The ruling, or None when the reply doesn't validate."""
    try:
        return Ruling.model_validate_json(content)
    except ValidationError:
        return None


def unresolved(cites: list[str], known: set[str]) -> list[str]:
    """The cites that name no corpus path, in the order given."""
    return [cite for cite in cites if cite not in known]


def build_prompt(question: str, entries: list[Entry]) -> str:
    """The instructions, the entries under their paths, then the question."""
    parts = [INSTRUCTIONS, render_markdown(entries), f"Question: {question}"]
    return "\n\n".join(parts)


def ollama_answer(prompt: str) -> str:
    """The model's raw reply to the prompt, an empty string when there is none."""
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        format=Ruling.model_json_schema(),
        think=THINK,
        options={
            "temperature": TEMPERATURE,
            "seed": SEED,
            "num_ctx": NUM_CTX,
        },
    )
    return response.message.content or ""
