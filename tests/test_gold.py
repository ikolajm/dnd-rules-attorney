"""Tests that the gold set's ids are unique and its cites are corpus paths."""

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from rules_attorney.corpus import load_corpus

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "srd-5.1"
GOLD = ROOT / "gold"
GOLD_FILES = ["gold.json", "gold.example.json"]
STATUSES = {"settled", "contested", "rules-as-intended"}
SPLITS = {"dev", "test"}


def load_gold(name: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = json.loads((GOLD / name).read_text(encoding="utf-8"))
    return items


@pytest.mark.parametrize("name", GOLD_FILES)
def test_gold_ids_unique_and_cites_resolve(name: str) -> None:
    items = load_gold(name)
    paths = {e.path for e in load_corpus(DATA)}

    failures: list[str] = []
    ids = Counter(item["id"] for item in items)
    for item_id, n in ids.items():
        if n > 1:
            failures.append(f"duplicate id: {item_id}")
    for item in items:
        for cite in item["cites"]:
            if cite not in paths:
                failures.append(f"{item['id']}: no such path: {cite}")

    assert failures == []


@pytest.mark.parametrize("name", GOLD_FILES)
def test_gold_labels_are_complete(name: str) -> None:
    failures: list[str] = []
    for item in load_gold(name):
        labeled = bool(item["verdict"] or item["ruling"] or item["cites"])
        if labeled and item["status"] not in STATUSES:
            failures.append(f"{item['id']}: bad status: {item['status']!r}")
        if item["status"] == "contested" and item["verdict"]:
            failures.append(f"{item['id']}: contested item has a verdict")
        if "split" in item and item["split"] not in SPLITS:
            failures.append(f"{item['id']}: bad split: {item['split']!r}")
        # The example's sample item is never split; only the real set must be.
        if name == "gold.json" and labeled and "split" not in item:
            failures.append(f"{item['id']}: no split; run scripts/split_gold.py")

    assert failures == []
