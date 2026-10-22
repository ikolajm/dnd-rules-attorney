"""Assign dev or test to every gold item in gold/gold.json without a split.

A split already assigned is never changed. Run this after new labels are added
and before anything is tuned against them, so no run sees an unassigned item.
"""

import json
from pathlib import Path

from rules_attorney.split import assign_splits

GOLD = Path(__file__).resolve().parent.parent / "gold" / "gold.json"


def main() -> None:
    """Read gold.json, assign the missing splits, and write it back."""
    items = json.loads(GOLD.read_text(encoding="utf-8"))
    split = assign_splits(items)
    text = json.dumps(split, indent=2, ensure_ascii=False) + "\n"

    GOLD.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
