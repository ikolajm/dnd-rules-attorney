"""Tests that the rescore runs every published row in order and stops when it should."""

from pathlib import Path

import pytest

from rules_attorney.evals.rescore import (
    HOSTED,
    MODELS,
    STAGED,
    Ref,
    RescoreError,
    Step,
    manifest_text,
    plan,
    read_manifest,
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


PUBLISHED = [
    *(
        f"answer {model}{suffix}"
        for model in MODELS
        for suffix in (
            ("", " rerank", " lookup", " level3", " loop") if model in STAGED else ("",)
        )
    ),
    "floor",
]


def test_table_rows_follow_the_published_order() -> None:
    (table,) = [step for step in plan() if step.name == "table"]

    assert table.args[0] == "--table"
    assert refs(table) == PUBLISHED


def test_judges_follow_the_published_order() -> None:
    judged = [
        ref for step in plan() if step.script == "judge_dev.py" for ref in refs(step)
    ]

    assert judged == PUBLISHED


def calls_api(step: Step) -> bool:
    return step.script == "judge_dev.py" or HOSTED in step.args


def test_every_local_run_comes_before_the_api_is_called() -> None:
    steps = plan()
    first_api = next(n for n, step in enumerate(steps) if calls_api(step))
    local = [n for n, step in enumerate(steps) if step.writes and not calls_api(step)]

    assert first_api == local[-1] + 1
    assert steps[first_api].name == f"agentic {HOSTED}"


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
OLD_PATH = Path("runs/old.jsonl")
OLD = {OLD_PATH: 1}
NEW = Path("runs/new.jsonl")


def test_written_finds_the_one_new_record() -> None:
    assert written(WRITES, OLD, {**OLD, NEW: 2}) == NEW


def test_written_finds_a_rewritten_record() -> None:
    # A judge rerun overwrites the file the failed judge half wrote.
    assert written(WRITES, OLD, {OLD_PATH: 2}) == OLD_PATH


@pytest.mark.parametrize(
    "added", [{}, {Path("runs/a.jsonl"): 2, Path("runs/b.jsonl"): 2}]
)
def test_written_refuses_none_or_two(added: dict[Path, int]) -> None:
    with pytest.raises(RescoreError, match="not one"):
        written(WRITES, OLD, {**OLD, **added})


def test_written_allows_none_from_a_quiet_step() -> None:
    assert written(QUIET, OLD, dict(OLD)) is None


def test_written_refuses_a_record_from_a_quiet_step() -> None:
    with pytest.raises(RescoreError, match="should not"):
        written(QUIET, OLD, {**OLD, NEW: 2})


def test_manifest_reads_back_what_it_wrote() -> None:
    records = {"retrieval": OLD_PATH, "floor": NEW}
    text = manifest_text("abc", records)

    assert read_manifest(text, "abc", {OLD_PATH, NEW}) == records


def test_manifest_refuses_another_commit() -> None:
    text = manifest_text("abc", {"retrieval": OLD_PATH})

    with pytest.raises(RescoreError, match="not def"):
        read_manifest(text, "def", {OLD_PATH})


def test_manifest_refuses_a_record_gone_from_runs() -> None:
    text = manifest_text("abc", {"retrieval": OLD_PATH, "floor": NEW})

    with pytest.raises(RescoreError, match="no longer in runs"):
        read_manifest(text, "abc", {OLD_PATH})


START = {"commit": "abc", "dirty": False}


def test_refuse_moved_passes_the_same_clean_tree() -> None:
    refuse_moved(START, dict(START))


def test_refuse_moved_refuses_a_dirty_tree() -> None:
    with pytest.raises(RescoreError, match="dirty"):
        refuse_moved(START, {"commit": "abc", "dirty": True})


def test_refuse_moved_refuses_a_moved_head() -> None:
    with pytest.raises(RescoreError, match="HEAD moved"):
        refuse_moved(START, {"commit": "def", "dirty": False})
