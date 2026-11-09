"""The test rescore's steps, in order, and the checks between them."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

# The models whose every stage is published, each with its loop.
STAGED = ("claude-opus-5-5", "qwen3.5:9b")
# Every answering model, in the published table's order.
MODELS = (
    "claude-opus-5-5",
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


def plan() -> list[Step]:
    """Every step of the rescore, in the order it runs."""
    steps = [
        Step("retrieval", "eval_retrieval.py", TEST, True),
        Step("rerank", "eval_rerank.py", TEST, True),
        Step("lookup", "eval_lookup.py", TEST, True),
    ]
    steps += [
        Step(f"agentic {model}", "eval_agentic.py", (model, *TEST), True)
        for model in STAGED
    ]
    answers = [step for model in MODELS for step in answer_steps(model)]
    floor = Step("floor", "floor_dev.py", TEST, True)
    steps += [*answers, floor]
    steps += [
        Step(f"judge {step.name}", "judge_dev.py", (Ref(step.name),), True)
        for step in [*answers, floor]
    ]
    steps.append(
        Step(
            "table",
            "summarize_runs.py",
            ("--table", *(Ref(step.name) for step in [*answers, floor])),
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
            tuple(Ref(step.name) for step in answers),
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


def written(step: Step, before: set[Path], after: set[Path]) -> Path | None:
    """The one record a step wrote, or None for a step that writes none."""
    new = sorted(after - before)
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
