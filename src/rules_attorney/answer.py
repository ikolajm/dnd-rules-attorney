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


def unresolved(cites: list[str], known: set[str]) -> list[str]:
    """The cites that name no corpus path, in the order given."""
    return [cite for cite in cites if cite not in known]
