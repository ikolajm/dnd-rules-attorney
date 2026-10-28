"""Tests for the planning step."""

from rules_attorney.multihop import build_plan_prompt, parse_plan

# A reply that names its list anything but sub_questions.
WRONG_FIELD_REPLY = '{"questions": ["Does being grappled set speed to 0?"]}'


def test_parse_plan_counts_a_missing_list_as_a_failure() -> None:
    assert parse_plan(WRONG_FIELD_REPLY) is None


def test_build_plan_prompt_carries_the_question() -> None:
    # Halfling appears nowhere in the instructions, so only the question
    # can put it in the prompt.
    question = "Can a halfling move through a hostile ogre's space?"
    assert question in build_plan_prompt(question)
