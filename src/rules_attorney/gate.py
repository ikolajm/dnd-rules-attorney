"""The gate step, from a question to whether it is about the rules at all."""

import ollama
from pydantic import BaseModel, ValidationError

from rules_attorney.answer import chat_request

GATE_INSTRUCTIONS = (
    "Decide whether the question below asks how the rules of Dungeons & "
    "Dragons fifth edition play out: what an action, condition, spell or "
    "weapon property does, or how one rule meets another at the table. "
    "A question about anything other than Dungeons & Dragons is not about "
    "the rules, even when it uses a word the rules use. "
    "When the question might be about the rules, count it as about the rules."
)


class Gate(BaseModel):
    """The gate a model returns: whether a question is about the rules."""

    about_rules: bool


def build_gate_prompt(question: str) -> str:
    """The instructions, then the question."""
    parts = [GATE_INSTRUCTIONS, f"Question: {question}"]
    return "\n\n".join(parts)


def parse_gate(content: str) -> bool | None:
    """Whether it is about the rules, or None when the reply doesn't validate."""
    try:
        return Gate.model_validate_json(content).about_rules
    except ValidationError:
        return None


def ollama_gate(prompt: str, *, model: str) -> str:
    """The model's raw reply to the prompt, an empty string when there is none."""
    response = ollama.chat(**chat_request(prompt, model, Gate.model_json_schema()))
    return response.message.content or ""
