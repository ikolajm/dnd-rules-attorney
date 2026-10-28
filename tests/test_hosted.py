"""Tests for the hosted answering step."""

from rules_attorney.hosted import PLAN_SCHEMA, RULING_SCHEMA


def test_ruling_schema_keeps_each_kind_as_an_enum() -> None:
    # The SDK's rewrite moves a const into the description, so a kind sent
    # as a const would reach the grammar unenforced.
    defs = RULING_SCHEMA["$defs"]
    assert defs
    for definition in defs.values():
        enum = definition["properties"]["kind"]["enum"]
        assert len(enum) == 1


def test_plan_schema_requires_the_sub_questions() -> None:
    # Required, the API's grammar cannot return a plan without its list.
    assert "sub_questions" in PLAN_SCHEMA.get("required", [])
