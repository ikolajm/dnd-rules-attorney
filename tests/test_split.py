"""Tests that gold splits are assigned once, reproducibly, and to target."""

from collections import Counter
from typing import Any

from rules_attorney.split import assign_splits


def make(item_id: str, status: str, split: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"id": item_id, "status": status}
    if split is not None:
        item["split"] = split
    return item


def splits_by_id(items: list[dict[str, Any]]) -> dict[str, str]:
    return {item["id"]: item["split"] for item in items}


def test_existing_split_never_changes() -> None:
    first = assign_splits([make(f"old-{n}", "contested") for n in range(10)])
    added = [make(f"new-{n}", "contested") for n in range(3)]
    second = assign_splits(first + added)

    before = splits_by_id(first)
    after = splits_by_id(second)
    assert {item_id: after[item_id] for item_id in before} == before


def test_same_input_same_output() -> None:
    items = [make(f"item-{n}", "settled") for n in range(10)]

    assert assign_splits(items) == assign_splits(items)


def test_dev_filled_to_target_per_status() -> None:
    contested = [
        make(f"contested-{n}", "contested", "dev" if n < 2 else None) for n in range(10)
    ]
    settled = [make(f"settled-{n}", "settled") for n in range(5)]

    result = assign_splits(contested + settled)

    counts = Counter((item["status"], item["split"]) for item in result)
    assert counts == {
        ("contested", "dev"): 6,
        ("contested", "test"): 4,
        ("settled", "dev"): 3,
        ("settled", "test"): 2,
    }
