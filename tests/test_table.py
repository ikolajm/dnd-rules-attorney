"""Tests for the scores the published table is built from."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from rules_attorney.table import Row, build_row, markdown_table

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


def test_markdown_table_refuses_runs_of_two_splits() -> None:
    dev = floor_row()
    with pytest.raises(ValueError, match="more than one split"):
        markdown_table([dev, replace(dev, split="test")])
