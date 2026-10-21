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


@pytest.mark.parametrize("name", ["gold.json", "gold.example.json"])
def test_gold_ids_unique_and_cites_resolve(name: str) -> None:
    text = (GOLD / name).read_text(encoding="utf-8")
    items: list[dict[str, Any]] = json.loads(text)
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
