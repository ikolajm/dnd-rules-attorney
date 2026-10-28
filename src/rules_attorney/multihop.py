"""The planning step, from a dispute to its sub-questions and one merged ranking."""

import ollama
from pydantic import BaseModel, ValidationError

from rules_attorney.answer import NUM_CTX, NUM_PREDICT, SEED, TEMPERATURE, THINK

PLAN_INSTRUCTIONS = (
    "List the separate rules questions the dispute below turns on, each one a "
    "question a single rule answers. "
    "When the dispute turns on one rule, give an empty list."
)


class Plan(BaseModel):
    """The plan a model returns: the separate rules questions a dispute turns on."""

    sub_questions: list[str]


def build_plan_prompt(question: str) -> str:
    """The instructions, then the question."""
    parts = [PLAN_INSTRUCTIONS, f"Question: {question}"]
    return "\n\n".join(parts)


def parse_plan(content: str) -> list[str] | None:
    """The sub-questions, or None when the reply doesn't validate."""
    try:
        return Plan.model_validate_json(content).sub_questions
    except ValidationError:
        return None


def ollama_plan(prompt: str, *, model: str) -> str:
    """The model's raw reply to the prompt, an empty string when there is none."""
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        format=Plan.model_json_schema(),
        think=THINK,
        options={
            "temperature": TEMPERATURE,
            "seed": SEED,
            "num_ctx": NUM_CTX,
            "num_predict": NUM_PREDICT,
        },
    )
    return response.message.content or ""
