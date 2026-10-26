"""The answering step, from retrieved entries to a validated ruling."""

import ollama
from pydantic import BaseModel, ValidationError

from rules_attorney.corpus import Entry, render_markdown

MODEL = "qwen3.5:9b"
SEED = 1
TEMPERATURE = 0.0
THINK = False
NUM_CTX = 16384

# What a verdict is, written once and sent word for word to the answering
# model and to the judge, so both work from the same sentence.
VERDICT = (
    "The verdict answers the question asked, in a few words: yes or no to a "
    "yes-or-no question, a number to a how-many question, the thing itself to "
    "a what question."
)
INSTRUCTIONS = (
    "Rule on the dispute below using only the rules entries given, and nothing "
    f"else. {VERDICT} Cite each entry your ruling rests on by its path: the text "
    "after the ## marker, written exactly, without the marker itself. In the "
    "explanation, give the rule, the fact from the question it applies to, and "
    "the conclusion. "
    "Set ambiguous to true when two entries conflict, or when your conclusion "
    "turns on a word or phrase the entries use that the text also lets you read "
    "another way, and that other reading gives a different verdict. "
    "In the explanation, before the flag, name the word or phrase your conclusion "
    "turns on and say whether the text allows it another reading. "
    "When ambiguous, give each reading and say why the text does not decide "
    "between them. "
    "Set ambiguous to true as well when an entry you cite, read word for word, "
    "gives a different verdict than the reason the entries give for that rule. "
    "Give the verdict the reason supports, and in the explanation say what the "
    "text as written would rule. "
    "A case the entries never address is not ambiguous on that ground alone: "
    "ambiguity is in the words the entries use, not in what they leave out."
)


class Ruling(BaseModel):
    """The ruling a model returns."""

    # Model writes the fields in the order they're declared,
    # so it gives its reasoning and the flag before it commits to a verdict.
    explanation: str
    ambiguous: bool
    verdict: str
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


def unmarked(cites: list[str]) -> list[str]:
    """The cites with a leading ## marker removed, the model's commonest slip."""
    return [cite.removeprefix("## ") for cite in cites]


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
