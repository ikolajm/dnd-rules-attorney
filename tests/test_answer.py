"""Tests for the answering step."""

from pathlib import Path

from rules_attorney.answer import (
    VERDICT,
    build_prompt,
    parse_reply,
    unmarked,
    unresolved,
)
from rules_attorney.corpus import Entry, load_corpus

DATA = Path(__file__).resolve().parent.parent / "data" / "srd-5.1"

# Replies captured from a probe of qwen3.5 through Ollama's structured output.
# qwen3.5:0.8b with thinking on returned no content at all.
EMPTY_REPLY = ""
# qwen3.5:9b, thinking off, against a schema that had no explanation field.
NO_EXPLANATION_REPLY = '{"verdict": "Yes", "ambiguous": false, "cites": ["PHB p.195"]}'


def test_parse_reply_counts_an_empty_reply_as_a_failure() -> None:
    assert parse_reply(EMPTY_REPLY) is None


def test_parse_reply_counts_a_missing_field_as_a_failure() -> None:
    assert parse_reply(NO_EXPLANATION_REPLY) is None


def test_parse_reply_returns_the_ruling_given() -> None:
    reply = (
        '{"verdict": "Yes", "explanation": "Grappled only sets speed to 0.", '
        '"ambiguous": false, "cites": ["conditions > grappled"]}'
    )
    ruling = parse_reply(reply)
    assert ruling is not None
    assert ruling.verdict == "Yes"
    assert ruling.cites == ["conditions > grappled"]


def test_parse_reply_accepts_a_bare_integer_verdict() -> None:
    # The shape qwen3.5:9b wrote for a how-many question once the verdict could
    # be an integer. Held to a string, it wrote "}" there instead.
    reply = (
        '{"explanation": "A separate save is made for each source of damage.", '
        '"ambiguous": false, "verdict": 2, '
        '"cites": ["casting-a-spell > duration > concentration"]}'
    )
    ruling = parse_reply(reply)
    assert ruling is not None
    assert ruling.verdict == 2


def test_unresolved_keeps_only_cites_outside_the_corpus() -> None:
    known = {entry.path for entry in load_corpus(DATA)}
    # cover is a root path, cited alone; PHB p.195 is a cite qwen3.5:9b made up.
    assert unresolved(["cover", "PHB p.195"], known) == ["PHB p.195"]


def test_unmarked_removes_only_a_leading_marker() -> None:
    # The first is a cite qwen3.5:9b wrote in a dev run, the header copied in.
    cites = ["## conditions > grappled", "cover"]
    assert unmarked(cites) == ["conditions > grappled", "cover"]


def test_build_prompt_carries_every_path_and_the_question() -> None:
    entries = [
        Entry("conditions > grappled", "Grappled\n\nSpeed becomes 0."),
        Entry("cover", "Cover\n\nWalls can provide cover."),
    ]
    prompt = build_prompt("Can a grappled creature hide?", entries)
    # A model cannot cite a path it never saw.
    for entry in entries:
        assert f"## {entry.path}" in prompt
    assert "Can a grappled creature hide?" in prompt


def test_build_prompt_defines_the_verdict() -> None:
    # Without it the model guesses from the field name, and answered a
    # how-many question with "true".
    prompt = build_prompt("q", [])
    assert VERDICT in prompt
