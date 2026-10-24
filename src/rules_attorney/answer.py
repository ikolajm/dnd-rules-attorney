"""The answering step, from retrieved entries to a validated ruling."""

from pydantic import BaseModel, ValidationError


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
