"""The planning step, from a dispute to its sub-questions and one merged ranking."""

import ollama
from pydantic import BaseModel, ValidationError

from rules_attorney.answer import NUM_CTX, NUM_PREDICT, SEED, TEMPERATURE, THINK
from rules_attorney.fusion import fuse

PLAN_INSTRUCTIONS = (
    "List the separate rules the dispute below turns on, as one short question "
    "per rule. Each question names the rule, condition, spell or action it asks "
    "about, the way a rulebook's index would, and leaves out the dispute's own "
    "details. Leave out any rule the dispute does not need. "
    "Never restate the dispute as a question. "
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


def merged_ranking(question: list[str], subs: list[list[str]]) -> list[str]:
    """The question's ranking and the sub-questions', fused into one."""
    return fuse([question, *subs])
