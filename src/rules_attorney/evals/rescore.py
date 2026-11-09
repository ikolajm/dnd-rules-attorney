"""The test rescore's steps, in order, and the checks between them."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HOSTED = "claude-opus-5-5"
# The models whose every stage is published, each with its loop.
STAGED = (HOSTED, "qwen3.5:9b")
# Every answering model, in the published table's order.
MODELS = (
    HOSTED,
    "gemma4:12b",
    "qwen3.5:9b",
    "qwen3.5:4b",
    "qwen3.5:2b",
    "qwen3.5:0.8b",
    "ministral-3:8b",
    "olmo-3:7b-instruct",
)
# Each stage after level 1, as answer_dev's flags, the loop's added per model.
STAGES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("rerank", ("--rerank",)),
    ("lookup", ("--lookup",)),
    ("level3", ("--level", "3")),
)
TEST = ("--split", "test")


class RescoreError(Exception):
    """The rescore stops: a step wrote the wrong records, or the tree moved."""


@dataclass(frozen=True)
class Ref:
    """The record an earlier step wrote, filled in when this step runs."""

    step: str


@dataclass(frozen=True)
class Step:
    """One script call: its name, the script, its arguments, what it writes."""

    name: str
    script: str
    args: tuple[str | Ref, ...]
    # Whether it writes one record to runs/; a step that does not writes none.
    writes: bool


def answer_steps(model: str) -> list[Step]:
    """A model's level 1 answer run, then each stage's if it is staged."""
    steps = [Step(f"answer {model}", "answer_dev.py", (model, *TEST), True)]
    if model in STAGED:
        for stage, flags in STAGES:
            steps.append(
                Step(
                    f"answer {model} {stage}",
                    "answer_dev.py",
                    (model, *TEST, *flags),
                    True,
                )
            )
        steps.append(
            Step(
                f"answer {model} loop",
                "answer_dev.py",
                (model, *TEST, "--loop-records", Ref(f"agentic {model}")),
                True,
            )
        )
    return steps


def loop_step(model: str) -> Step:
    """The model's agentic loop over test."""
    return Step(f"agentic {model}", "eval_agentic.py", (model, *TEST), True)


def plan() -> list[Step]:
    """Every step of the rescore, in the order it runs.

    Every local run comes before the hosted model's, so a failure in a path
    they share stops the rescore before it spends API credit. The judges and
    the table take the published table's order.
    """
    steps = [
        Step("retrieval", "eval_retrieval.py", TEST, True),
        Step("rerank", "eval_rerank.py", TEST, True),
        Step("lookup", "eval_lookup.py", TEST, True),
    ]
    local = [model for model in MODELS if model != HOSTED]
    steps += [loop_step(model) for model in STAGED if model != HOSTED]
    steps += [step for model in local for step in answer_steps(model)]
    floor = Step("floor", "floor_dev.py", TEST, True)
    steps += [floor, loop_step(HOSTED), *answer_steps(HOSTED)]

    published = [*(step for model in MODELS for step in answer_steps(model)), floor]
    steps += [
        Step(f"judge {step.name}", "judge_dev.py", (Ref(step.name),), True)
        for step in published
    ]
    steps.append(
        Step(
            "table",
            "summarize_runs.py",
            ("--table", *(Ref(step.name) for step in published)),
            False,
        )
    )
    for model in STAGED:
        for stage in (*(stage for stage, _flags in STAGES), "loop"):
            steps.append(
                Step(
                    f"gains {model} {stage}",
                    "summarize_runs.py",
                    ("--gains", Ref(f"answer {model}"), Ref(f"answer {model} {stage}")),
                    False,
                )
            )
    steps.append(
        Step(
            "handed",
            "score_handed.py",
            tuple(Ref(step.name) for step in published if step is not floor),
            False,
        )
    )
    steps += [
        Step(
            f"agentic {model} records",
            "eval_agentic.py",
            (model, *TEST, "--records", Ref(f"agentic {model}")),
            False,
        )
        for model in STAGED
    ]
    return steps


def resolve(step: Step, records: dict[str, Path]) -> list[str]:
    """The step's arguments, each Ref replaced by the record its step wrote."""
    args: list[str] = []
    for arg in step.args:
        if isinstance(arg, Ref):
            if arg.step not in records:
                raise RescoreError(f"{step.name}: no record from {arg.step!r}")
            args.append(str(records[arg.step]))
        else:
            args.append(arg)
    return args


def written(step: Step, before: dict[Path, int], after: dict[Path, int]) -> Path | None:
    """The one record a step wrote, or None for a step that writes none.

    Each listing maps a file to its modified time, so a file the step
    rewrote counts: a judge rerun overwrites the half-written file of the
    judge that failed.
    """
    new = sorted(path for path, mtime in after.items() if before.get(path) != mtime)
    if step.writes:
        if len(new) != 1:
            raise RescoreError(f"{step.name}: wrote {len(new)} records, not one: {new}")
        return new[0]
    if new:
        raise RescoreError(f"{step.name}: wrote records it should not: {new}")
    return None


def refuse_moved(start: dict[str, Any], now: dict[str, Any]) -> None:
    """Refuses a dirty tree, or a HEAD moved since the rescore started."""
    if now["dirty"]:
        raise RescoreError("the tree is dirty: commit or stash first")
    if now["commit"] != start["commit"]:
        raise RescoreError(f"HEAD moved from {start['commit']} to {now['commit']}")


def manifest_text(commit: str, records: dict[str, Path]) -> str:
    """The steps done at the commit and the record each wrote, as JSON."""
    paths = {name: path.as_posix() for name, path in records.items()}
    return json.dumps({"commit": commit, "records": paths}, indent=2) + "\n"


def read_manifest(text: str, commit: str, exists: set[Path]) -> dict[str, Path]:
    """A stopped rescore's records, refused if one is gone or the commit differs."""
    data = json.loads(text)
    if data["commit"] != commit:
        raise RescoreError(f"the manifest is for {data['commit']}, not {commit}")
    records = {name: Path(path) for name, path in data["records"].items()}
    missing = sorted(str(path) for path in records.values() if path not in exists)
    if missing:
        raise RescoreError(f"the manifest names records no longer in runs/: {missing}")
    return records
