"""Tests for the planning step."""

from rules_attorney.multihop import build_plan_prompt, merged_ranking, parse_plan

# A reply that names its list anything but sub_questions.
WRONG_FIELD_REPLY = '{"questions": ["Does being grappled set speed to 0?"]}'
# A question's ranking ten deep, so it has a tenth.
QUESTION_RANKING = [f"q{place}" for place in range(1, 11)]


def test_parse_plan_counts_a_missing_list_as_a_failure() -> None:
    assert parse_plan(WRONG_FIELD_REPLY) is None


def test_build_plan_prompt_carries_the_question() -> None:
    # Halfling appears nowhere in the instructions, so only the question
    # can put it in the prompt.
    question = "Can a halfling move through a hostile ogre's space?"
    assert question in build_plan_prompt(question)


def test_merged_ranking_with_no_sub_questions_is_the_question_ranking() -> None:
    assert merged_ranking(QUESTION_RANKING, []) == QUESTION_RANKING


def test_merged_ranking_puts_a_sub_question_first_into_the_top_ten() -> None:
    # Absent from the question's ranking, so it scores on its first place
    # alone: 1/61 against the question's tenth at 1/70.
    merged = merged_ranking(QUESTION_RANKING, [["sub-first"]])
    assert "sub-first" in merged[:10]
    assert "q10" not in merged[:10]
