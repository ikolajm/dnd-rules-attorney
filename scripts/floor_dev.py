"""Writes the floor's records: "no" to every item, never flagged, no cites.

    python scripts/floor_dev.py [--split dev|test]

Calls nothing. The records take the shape scripts/answer_dev.py writes, so
scripts/judge_dev.py judges them like any other run, and the floor's agreement
is measured rather than counted from gold's wording.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rules_attorney.answer import Ruling, YesOrNo
from rules_attorney.provenance import commit
from rules_attorney.split import SPLITS

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
GOLD = ROOT / "gold" / "gold.json"

# Built through the model, so a floor that no longer fits the schema fails
# here rather than at judging.
FLOOR = Ruling(
    explanation="",
    ambiguous=False,
    answer=YesOrNo(kind="yes-or-no", verdict="no"),
    cites=[],
)


def main() -> None:
    """Write one floor record per item of the split."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--split", choices=SPLITS, default=SPLITS[0])
    split: str = parser.parse_args().split
    items: list[dict[str, Any]] = json.loads(GOLD.read_text(encoding="utf-8"))
    chosen = [item for item in items if item["split"] == split]
    source = commit(ROOT)
    config: dict[str, Any] = {
        "model": "floor",
        "split": split,
        "fields": list(Ruling.model_fields),
        "commit": source["commit"],
        "dirty": source["dirty"],
    }

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"{stamp}-{split}-floor.jsonl"
    with out.open("w", encoding="utf-8") as file:
        for item in chosen:
            record = {
                "id": item["id"],
                "retrieved": [],
                "reply": FLOOR.model_dump_json(),
                "ruling": FLOOR.model_dump(),
                "unresolved": [],
                "seconds": 0,
                "config": config,
            }
            file.write(json.dumps(record) + "\n")

    print(out)


if __name__ == "__main__":
    main()
