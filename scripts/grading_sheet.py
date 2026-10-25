"""Writes a blind hand-grading template for a run: gold and system verdicts, no judge.

The template goes to gold/hand-grades-<run stem>.json, one file per run.

The items are chosen by a fixed rule, in the run file's order, so the choice
is made before anything is read: every rules-as-intended item, and every
third settled item. Contested items have no verdict and are never chosen.
Each item's agrees field starts as null, to be set to true or false by hand.
"""

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "gold" / "gold.json"
SETTLED_STEP = 3


def grades_path(run_name: str) -> Path:
    """Where the hand grades for a run live, named after the run."""
    return ROOT / "gold" / f"hand-grades-{Path(run_name).stem}.json"


def main() -> None:
    """Write the chosen items, each with an empty agrees field."""
    run = Path(sys.argv[1])
    grades_file = grades_path(run.name)
    if grades_file.exists():
        sys.exit(f"{grades_file} exists; not overwriting it.")
    gold: dict[str, dict[str, Any]] = {
        item["id"]: item for item in json.loads(GOLD.read_text(encoding="utf-8"))
    }
    records: list[dict[str, Any]] = [
        json.loads(line) for line in run.open(encoding="utf-8")
    ]

    intended = [r for r in records if gold[r["id"]]["status"] == "rules-as-intended"]
    settled = [r for r in records if gold[r["id"]]["status"] == "settled"]
    chosen = intended + settled[::SETTLED_STEP]

    grades: dict[str, dict[str, Any]] = {}
    for record in chosen:
        item = gold[record["id"]]
        answer = record["ruling"]
        grades[record["id"]] = {
            "status": item["status"],
            "question": item["question"],
            "gold_verdict": item["verdict"],
            "gold_ruling": item["ruling"],
            "system_verdict": answer["verdict"] if answer is not None else None,
            "agrees": None,
        }

    template = {
        "run": run.name,
        "asks": "Does the system verdict mean the same as the gold verdict?",
        "grades": grades,
    }
    grades_file.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
    print(f"{grades_file}: {len(chosen)} items to grade.")


if __name__ == "__main__":
    main()
