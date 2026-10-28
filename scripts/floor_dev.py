"""Writes the floor's records: "no" to every dev item, never flagged, no cites.

Calls nothing. The records take the shape scripts/answer_dev.py writes, so
scripts/judge_dev.py judges them like any other run, and the floor's agreement
is measured rather than counted from gold's wording.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rules_attorney.answer import Ruling, YesOrNo
from rules_attorney.provenance import commit

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
    """Write one floor record per dev item."""
    items: list[dict[str, Any]] = json.loads(GOLD.read_text(encoding="utf-8"))
    dev = [item for item in items if item["split"] == "dev"]
    source = commit(ROOT)
    config: dict[str, Any] = {
        "model": "floor",
        "fields": list(Ruling.model_fields),
        "commit": source["commit"],
        "dirty": source["dirty"],
    }

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"{stamp}-floor.jsonl"
    with out.open("w", encoding="utf-8") as file:
        for item in dev:
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
