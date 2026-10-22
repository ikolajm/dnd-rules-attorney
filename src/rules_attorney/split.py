"""Assign dev or test to each gold item without a split, never changing one."""

import random
from typing import Any

SEED: int = 7
DEV_SHARE: float = 0.6


def assign_splits(
    items: list[dict[str, Any]], seed: int = SEED
) -> list[dict[str, Any]]:
    """Return a copy of items with a split given to each item that has none."""
    out = [dict(item) for item in items]
    by_status: dict[str, list[dict[str, Any]]] = {}

    for item in out:
        by_status.setdefault(item["status"], []).append(item)
    rng = random.Random(seed)

    for status in sorted(by_status):
        group = by_status[status]
        unsplit = [item for item in group if "split" not in item]
        have_dev = sum(1 for item in group if item.get("split") == "dev")
        need = max(0, round(len(group) * DEV_SHARE) - have_dev)
        rng.shuffle(unsplit)

        for i, item in enumerate(unsplit):
            item["split"] = "dev" if i < need else "test"

    return out
