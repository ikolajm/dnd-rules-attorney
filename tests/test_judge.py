"""Tests for the judge."""

from pathlib import Path

from anthropic.types import Message

from rules_attorney.answer import KIND, VERDICT
from rules_attorney.judge import (
    build_judge_prompt,
    flag_correct,
    needs_judge,
    parse_judgement,
    reply_text,
)

CAPTURED = Path(__file__).resolve().parent / "captured" / "judge-response.json"


def test_flag_correct_misses_a_contested_item_left_unflagged() -> None:
    assert not flag_correct("contested", False)


def test_flag_correct_refuses_a_settled_item_flagged() -> None:
    assert not flag_correct("settled", True)


def test_flag_correct_expects_a_rules_as_intended_item_flagged() -> None:
    # Its text alone does not settle it, so it is flagged like a contested one.
    assert flag_correct("rules-as-intended", True)


def test_needs_judge_holds_back_a_contested_item() -> None:
    # A contested item has an empty verdict, so there is nothing to match.
    assert not needs_judge("contested")


def test_parse_judgement_counts_a_missing_reason_as_a_failure() -> None:
    assert parse_judgement('{"agrees": true}') is None


def test_parse_judgement_counts_an_extra_field_as_a_failure() -> None:
    # The API's structured output needs a schema that forbids extra fields;
    # this goes red if Judgement stops forbidding them.
    reply = '{"agrees": true, "reason": "Both say no.", "confidence": 0.9}'
    assert parse_judgement(reply) is None


def test_build_judge_prompt_carries_all_four_inputs() -> None:
    prompt = build_judge_prompt(
        "Can a grappled creature cast a spell?",
        "yes",
        "Grappled only sets speed to 0.",
        "Yes, it can still cast.",
    )
    assert "Can a grappled creature cast a spell?" in prompt
    assert "yes" in prompt
    assert "Grappled only sets speed to 0." in prompt
    assert "Yes, it can still cast." in prompt


def test_build_judge_prompt_labels_the_verdict_as_the_instructions_name_it() -> None:
    # The instructions ask about "the system's verdict"; a label that names it
    # differently leaves the model to guess which part that is.
    prompt = build_judge_prompt("q", "gold", "ruling", "answer")
    assert "System verdict: answer" in prompt


def test_build_judge_prompt_defines_the_verdict_as_the_answer_prompt_does() -> None:
    # The judge checks verdicts against the same sentence the answering model
    # was given, not a wording of its own.
    prompt = build_judge_prompt("q", "gold", "ruling", "answer")
    assert VERDICT in prompt


def test_build_judge_prompt_leaves_out_the_kind() -> None:
    # The judge compares verdicts, not kinds, and its instructions were checked
    # against hand grades; the kind's sentence would change them unchecked.
    prompt = build_judge_prompt("q", "gold", "ruling", "answer")
    assert KIND not in prompt


def test_reply_text_reads_a_captured_response() -> None:
    # One live call to claude-sonnet-5-5, saved whole, so a change in the shape
    # the API sends goes red here instead of in a run.
    message = Message.model_validate_json(CAPTURED.read_text(encoding="utf-8"))
    judgement = parse_judgement(reply_text(message))
    assert judgement is not None
