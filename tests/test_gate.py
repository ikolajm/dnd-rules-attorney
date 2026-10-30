"""Tests for the gate step."""

from rules_attorney.gate import build_gate_prompt, parse_gate

# The reply qwen3.5:0.8b gave the answering step with thinking on: no content
# at all. Ollama returns the same empty string from any call that produces none.
EMPTY_REPLY = ""
# A reply that names its bool anything but about_rules.
WRONG_FIELD_REPLY = '{"is_rules_question": true}'


def test_parse_gate_counts_an_empty_reply_as_a_failure() -> None:
    assert parse_gate(EMPTY_REPLY) is None


def test_parse_gate_counts_a_missing_field_as_a_failure() -> None:
    assert parse_gate(WRONG_FIELD_REPLY) is None


def test_build_gate_prompt_carries_the_question() -> None:
    # Halfling appears nowhere in the instructions, so only the question
    # can put it in the prompt.
    question = "Can a halfling move through a hostile ogre's space?"
    assert question in build_gate_prompt(question)
