"""Compares a judged run with the hand grades for the same run.

Each hand-graded item's agrees is set beside the judge's, and every item
where they differ is listed with the judge's reason.
"""

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    """Print how often the judge matched the hand grades, and where not."""
    judged_path = Path(sys.argv[1])
    judged: dict[str, dict[str, Any]] = {}
    for line in judged_path.open(encoding="utf-8"):
        record = json.loads(line)
        judged[record["id"]] = record

    runs = {record["config"]["run"] for record in judged.values()}
    if len(runs) != 1:
        sys.exit(f"judged file mixes runs: {runs}")
    run = runs.pop()
    # Named the way scripts/grading_sheet.py names it.
    grades_file = ROOT / "gold" / f"hand-grades-{Path(run).stem}.json"
    hand: dict[str, Any] = json.loads(grades_file.read_text(encoding="utf-8"))
    if hand["run"] != run:
        sys.exit(f"{grades_file} is for {hand['run']}, judged file is for {run}")

    matched = 0
    differ: list[str] = []
    for item_id, grade in hand["grades"].items():
        record = judged[item_id]
        if record["agrees"] == grade["agrees"]:
            matched += 1
        else:
            differ.append(item_id)

    judge_model = next(iter(judged.values()))["config"]["judge_model"]
    print(f"{judge_model} matched the hand grades on {matched} / {len(hand['grades'])}")
    for item_id in differ:
        grade = hand["grades"][item_id]
        record = judged[item_id]
        print(f"\n== {item_id} ({grade['status']})")
        print(f"Gold verdict: {grade['gold_verdict']}")
        print(f"System verdict: {grade['system_verdict']}")
        print(f"Hand: {grade['agrees']}, judge: {record['agrees']}")
        print(f"Judge reason: {record['reason']}")


if __name__ == "__main__":
    main()
