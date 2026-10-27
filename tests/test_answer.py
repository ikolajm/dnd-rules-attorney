"""Tests for the answering step."""

from pathlib import Path

from rules_attorney.answer import (
    KIND,
    VERDICT,
    Ruling,
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
        '{"explanation": "Grappled only sets speed to 0.", "ambiguous": false, '
        '"answer": {"kind": "yes-or-no", "verdict": "yes"}, '
        '"cites": ["conditions > grappled"]}'
    )
    ruling = parse_reply(reply)
    assert ruling is not None
    assert ruling.answer.kind == "yes-or-no"
    assert ruling.answer.verdict == "yes"
    assert ruling.cites == ["conditions > grappled"]


def test_parse_reply_accepts_a_bare_integer_verdict() -> None:
    # The shape qwen3.5:9b wrote for a how-many question once the verdict could
    # be an integer. Held to a string, it wrote "}" there instead.
    reply = (
        '{"explanation": "A separate save is made for each source of damage.", '
        '"ambiguous": false, "answer": {"kind": "how-many", "verdict": 2}, '
        '"cites": ["casting-a-spell > duration > concentration"]}'
    )
    ruling = parse_reply(reply)
    assert ruling is not None
    assert ruling.answer.kind == "how-many"
    assert ruling.answer.verdict == 2


def test_parse_reply_refuses_a_number_to_a_yes_or_no_question() -> None:
    # olmo-3:7b-instruct answered dodge-while-grappled with 0, its explanation
    # ending "Verdict: no".
    reply = (
        '{"explanation": "Speed drops to 0, so Dodge is lost.", "ambiguous": false, '
        '"answer": {"kind": "yes-or-no", "verdict": 0}, '
        '"cites": ["actions-in-combat > dodge"]}'
    )
    assert parse_reply(reply) is None


def test_parse_reply_refuses_a_word_that_is_not_yes_or_no() -> None:
    # ministral-3:8b answered grappled-gives-advantage with "set", a word from
    # the instruction to set ambiguous.
    reply = (
        '{"explanation": "The text allows two readings.", "ambiguous": true, '
        '"answer": {"kind": "yes-or-no", "verdict": "set"}, '
        '"cites": ["conditions > grappled"]}'
    )
    assert parse_reply(reply) is None


def test_ruling_schema_keeps_the_declared_field_order() -> None:
    # Ollama's grammar follows the schema's order, so the model reasons and
    # flags before it answers, and names the kind before the verdict.
    schema = Ruling.model_json_schema()
    assert list(schema["properties"]) == ["explanation", "ambiguous", "answer", "cites"]
    # Named first, so an empty $defs cannot pass the loop below.
    assert set(schema["$defs"]) == {"YesOrNo", "HowMany", "What"}
    for branch in schema["$defs"].values():
        assert list(branch["properties"]) == ["kind", "verdict"]


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


def test_build_prompt_defines_the_kind() -> None:
    # The grammar forces a kind but says nothing of what it is for; without the
    # sentence the model has only the field name, as the verdict once had.
    prompt = build_prompt("q", [])
    assert KIND in prompt
