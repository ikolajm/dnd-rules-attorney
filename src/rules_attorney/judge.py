"""The judge, scoring a run's rulings against the gold set."""

import anthropic
from anthropic.types import Message, TextBlock
from pydantic import BaseModel, ConfigDict, ValidationError

from rules_attorney.answer import VERDICT


class Judgement(BaseModel):
    """The judge's reply."""

    model_config = ConfigDict(extra="forbid")
    agrees: bool
    reason: str


JUDGE_MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 1024
JUDGE_INSTRUCTIONS = (
    "You are checking one answer to a tabletop rules question against a "
    "reference ruling. Decide whether the system's verdict means the same thing "
    "as the gold verdict, whatever the wording: 'no' and 'it cannot' agree. "
    "The gold ruling is given only to explain what a short gold verdict means. "
    "A verdict that takes both sides, or does not commit to one, does not agree. "
    f"{VERDICT} A system verdict that does not answer the question asked does "
    "not agree. Read 'true' and 'false' as yes and no. A verdict that reaches "
    "the gold answer agrees even if it leaves out conditions the gold verdict "
    "states. "
    "In reason, say in one plain sentence why the two verdicts agree or differ."
)


def flag_correct(status: str, ambiguous: bool) -> bool:
    """Whether the model's flag is right: settled unflagged, anything else flagged."""
    expected = status != "settled"
    return ambiguous == expected


def needs_judge(status: str) -> bool:
    """Whether the item has a verdict to judge; a contested item has none."""
    return status != "contested"


def build_judge_prompt(
    question: str, gold_verdict: str, gold_ruling: str, verdict: str
) -> str:
    """The judge's instructions, then each input under its own label."""
    parts = [
        JUDGE_INSTRUCTIONS,
        f"Question: {question}",
        f"Gold verdict: {gold_verdict}",
        f"Gold ruling: {gold_ruling}",
        f"System verdict: {verdict}",
    ]
    return "\n\n".join(parts)


def parse_judgement(content: str) -> Judgement | None:
    """The judgement, or None when the reply doesn't validate."""
    try:
        return Judgement.model_validate_json(content)
    except ValidationError:
        return None


def claude_judge(prompt: str) -> Message:
    """The judge's raw response to the prompt, a live call."""
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=MAX_TOKENS,
        # Sonnet 5.5's lowest setting; it rejects disabled.
        thinking={"type": "between_tools"},
        output_config={
            "format": {"type": "json_schema", "schema": Judgement.model_json_schema()}
        },
        messages=[{"role": "user", "content": prompt}],
    )
    return response


def reply_text(message: Message) -> str:
    """The reply's first text, or an empty string when there is none."""
    for block in message.content:
        if isinstance(block, TextBlock):
            return block.text
    return ""
