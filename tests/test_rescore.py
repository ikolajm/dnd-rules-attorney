"""Tests that the rescore runs every published row in order and stops when it should."""

from pathlib import Path

import pytest

from rules_attorney.evals.rescore import (
    MODELS,
    STAGED,
    Ref,
    RescoreError,
    Step,
    plan,
    refuse_moved,
    resolve,
    written,
)

ANSWERING = ("answer_dev.py", "floor_dev.py")


def refs(step: Step) -> list[str]:
    return [arg.step for arg in step.args if isinstance(arg, Ref)]


def test_names_are_unique() -> None:
    names = [step.name for step in plan()]

    assert len(names) == len(set(names))


def test_every_ref_names_an_earlier_step_that_writes() -> None:
    seen: set[str] = set()
    for step in plan():
        assert set(refs(step)) <= seen, step.name
        if step.writes:
            seen.add(step.name)


def test_every_call_that_takes_a_split_is_on_test() -> None:
    takes_split = (
        "eval_retrieval.py",
        "eval_rerank.py",
        "eval_lookup.py",
        "eval_agentic.py",
    )
    for step in plan():
        if step.script in takes_split + ANSWERING:
            index = step.args.index("--split")
            assert step.args[index + 1] == "test", step.name


def test_every_answer_run_and_the_floor_is_judged_once() -> None:
    steps = plan()
    answered = [step.name for step in steps if step.script in ANSWERING]
    judged = [
        ref for step in steps if step.script == "judge_dev.py" for ref in refs(step)
    ]

    assert sorted(judged) == sorted(answered)


def test_one_answer_run_per_published_row() -> None:
    answered = [step for step in plan() if step.script in ANSWERING]

    # Eight models at level 1, four more stages for each staged model, the floor.
    assert len(answered) == len(MODELS) + 4 * len(STAGED) + 1 == 17


def test_table_rows_follow_the_answer_order() -> None:
    steps = plan()
    answered = [step.name for step in steps if step.script in ANSWERING]
    (table,) = [step for step in steps if step.name == "table"]

    assert table.args[0] == "--table"
    assert refs(table) == answered


def test_each_loop_answers_from_its_own_models_agentic_record() -> None:
    for model in STAGED:
        (loop,) = [step for step in plan() if step.name == f"answer {model} loop"]

        assert refs(loop) == [f"agentic {model}"]


def test_gains_set_each_stage_against_its_models_level_1() -> None:
    gains = [step for step in plan() if step.args[:1] == ("--gains",)]
    pairs = {tuple(refs(step)) for step in gains}

    assert pairs == {
        (f"answer {model}", f"answer {model} {stage}")
        for model in STAGED
        for stage in ("rerank", "lookup", "level3", "loop")
    }


def test_only_the_tables_write_nothing() -> None:
    quiet = [step.script for step in plan() if not step.writes]

    assert set(quiet) == {"summarize_runs.py", "score_handed.py", "eval_agentic.py"}
    assert all(
        "--records" in step.args for step in plan() if step.name.endswith(" records")
    )


def test_resolve_fills_refs_with_records() -> None:
    step = Step("judge x", "judge_dev.py", ("--flag", Ref("x")), True)

    assert resolve(step, {"x": Path("runs/x.jsonl")}) == [
        "--flag",
        str(Path("runs/x.jsonl")),
    ]


def test_resolve_refuses_a_missing_record() -> None:
    step = Step("judge x", "judge_dev.py", (Ref("x"),), True)

    with pytest.raises(RescoreError, match="no record from 'x'"):
        resolve(step, {})


WRITES = Step("w", "answer_dev.py", (), True)
QUIET = Step("q", "score_handed.py", (), False)
OLD = {Path("runs/old.jsonl")}


def test_written_finds_the_one_new_record() -> None:
    new = Path("runs/new.jsonl")

    assert written(WRITES, OLD, OLD | {new}) == new


@pytest.mark.parametrize("added", [set(), {Path("runs/a.jsonl"), Path("runs/b.jsonl")}])
def test_written_refuses_none_or_two(added: set[Path]) -> None:
    with pytest.raises(RescoreError, match="not one"):
        written(WRITES, OLD, OLD | added)


def test_written_allows_none_from_a_quiet_step() -> None:
    assert written(QUIET, OLD, OLD) is None


def test_written_refuses_a_record_from_a_quiet_step() -> None:
    with pytest.raises(RescoreError, match="should not"):
        written(QUIET, OLD, OLD | {Path("runs/new.jsonl")})


START = {"commit": "abc", "dirty": False}


def test_refuse_moved_passes_the_same_clean_tree() -> None:
    refuse_moved(START, dict(START))


def test_refuse_moved_refuses_a_dirty_tree() -> None:
    with pytest.raises(RescoreError, match="dirty"):
        refuse_moved(START, {"commit": "abc", "dirty": True})


def test_refuse_moved_refuses_a_moved_head() -> None:
    with pytest.raises(RescoreError, match="HEAD moved"):
        refuse_moved(START, {"commit": "def", "dirty": False})
