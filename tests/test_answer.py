"""Tests for the answering step."""

from rules_attorney.answer import parse_reply

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
