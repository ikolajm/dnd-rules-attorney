"""Tests for the scores the published table is built from."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from rules_attorney.evals.table import (
    Row,
    build_row,
    gains,
    markdown_row,
    markdown_table,
)
from rules_attorney.rerank import RERANKER

# The floor's dev run and its judged file, copied from runs/: "no" to every
# item, never flagged, no cites, so each score is known in advance.
CAPTURED = Path(__file__).resolve().parent / "captured"


def load(name: str) -> list[dict[str, Any]]:
    """The records of a captured JSONL file."""
    lines = (CAPTURED / name).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def floor_row() -> Row:
    """The floor's row, built from its captured records."""
    judged = {record["id"]: record for record in load("floor-judged.jsonl")}
    return build_row(load("floor-run.jsonl"), judged, known=set())


def test_build_row_scores_the_captured_floor() -> None:
    row = floor_row()
    assert (row.agreed, row.judged) == (16, 32)
    assert row.failed == []
    assert row.cites == 0


def test_build_row_reads_the_flag_as_two_rates() -> None:
    # Dev holds ten expected-flagged items to thirty settled, so a count
    # over all forty would hide that the floor never flags.
    row = floor_row()
    assert (row.expected_flagged, row.expected) == (0, 10)
    assert (row.settled_flagged, row.settled) == (0, 30)


def test_build_row_reads_a_run_without_a_split_as_dev() -> None:
    # The captured floor predates the split in the config.
    assert floor_row().split == "dev"


def test_build_row_reads_a_run_without_a_level_as_level_1() -> None:
    # The captured floor predates the level in the config.
    assert floor_row().level == 1


def test_build_row_reads_a_run_without_a_reranker_as_none() -> None:
    # The captured floor predates the reranker in the config.
    assert floor_row().reranker is None


def test_build_row_reads_the_reranker() -> None:
    records = load("floor-run.jsonl")
    records[0]["config"]["reranker"] = RERANKER
    judged = {record["id"]: record for record in load("floor-judged.jsonl")}
    assert build_row(records, judged, known=set()).reranker == RERANKER


def test_build_row_reads_the_lookup() -> None:
    records = load("floor-run.jsonl")
    records[0]["config"]["lookup"] = ["equipment"]
    judged = {record["id"]: record for record in load("floor-judged.jsonl")}
    assert build_row(records, judged, known=set()).lookup == ["equipment"]


def test_build_row_reads_the_loop() -> None:
    records = load("floor-run.jsonl")
    records[0]["config"]["loop"] = "agentic-x.jsonl"
    judged = {record["id"]: record for record in load("floor-judged.jsonl")}
    assert build_row(records, judged, known=set()).loop == "agentic-x.jsonl"


def test_markdown_row_carries_the_level() -> None:
    row = replace(floor_row(), level=3)
    assert "| 3 |" in markdown_row(row)


def test_markdown_row_names_the_rerank_stage() -> None:
    # A rerank run records level 1, and must not print as one.
    row = replace(floor_row(), reranker=RERANKER)
    assert "| 1 + rerank |" in markdown_row(row)


def test_markdown_row_names_the_lookup_stage() -> None:
    row = replace(floor_row(), lookup=["equipment"])
    assert "| 1 + lookup |" in markdown_row(row)


def test_markdown_row_names_the_loop() -> None:
    # A loop run records level 1, and must not print as one.
    row = replace(floor_row(), loop="agentic-x.jsonl")
    assert "| loop |" in markdown_row(row)


def test_markdown_row_prints_a_dash_for_a_run_without_a_level() -> None:
    # The floor records its level as None. The published row's dash was once
    # typed by hand over the 1 a missing level printed.
    records = load("floor-run.jsonl")
    records[0]["config"]["level"] = None
    judged = {record["id"]: record for record in load("floor-judged.jsonl")}
    row = build_row(records, judged, known=set())
    assert "| floor | - |" in markdown_row(row)


def floor_judged() -> dict[str, dict[str, Any]]:
    """The captured floor's judged records, keyed by item id."""
    return {record["id"]: record for record in load("floor-judged.jsonl")}


def test_gains_names_the_item_each_run_agreed_on_alone() -> None:
    base = floor_judged()
    stage = floor_judged()
    # The floor disagrees on the first and agrees on the second.
    stage["grappled-attack-and-cast"]["agrees"] = True
    stage["grappled-gives-advantage"]["agrees"] = False
    assert gains(base, stage) == (
        ["grappled-attack-and-cast"],
        ["grappled-gives-advantage"],
    )


def test_gains_refuses_runs_of_different_items() -> None:
    stage = floor_judged()
    del stage["grappled-attack-and-cast"]
    with pytest.raises(ValueError, match="different items"):
        gains(floor_judged(), stage)


def test_markdown_table_refuses_runs_of_two_splits() -> None:
    dev = floor_row()
    with pytest.raises(ValueError, match="more than one split"):
        markdown_table([dev, replace(dev, split="test")])
