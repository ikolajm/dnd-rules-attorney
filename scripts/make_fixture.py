"""Writes level 3 records as the frontend's stream events, one fixture per record.

    python scripts/make_fixture.py <run file> <id> [<id> ...]

Each fixture is the event sequence the endpoint will send for that question:
`gate`, `plan`, `entries` and `ruling`, from a recorded run rather than a live
model, so the frontend renders real output before the endpoint exists. The
entries carry the corpus text the model was handed, in merged order.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from rules_attorney.corpus import load_corpus

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "srd-5.1"
GOLD = ROOT / "gold" / "gold.json"
FIXTURES = ROOT / "web" / "src" / "fixtures"

# The gate call is not written yet, so its event has no settled shape. This
# stands in for a question it lets through.
GATE_PLACEHOLDER = {"allowed": True}


def fixture(
    record: dict[str, Any],
    question: str,
    texts: dict[str, str],
    run: str,
) -> dict[str, Any]:
    """The record as the events the endpoint will send, in order."""
    entries = [{"path": path, "text": texts[path]} for path in record["retrieved"]]
    return {
        "source": {
            "run": run,
            "id": record["id"],
            "model": record["config"]["model"],
            "commit": record["config"]["commit"],
            "gate": "placeholder",
        },
        "question": question,
        "events": [
            {"event": "gate", "data": GATE_PLACEHOLDER},
            {"event": "plan", "data": {"sub_questions": record["sub_questions"]}},
            {"event": "entries", "data": {"entries": entries}},
            {"event": "ruling", "data": record["ruling"]},
        ],
    }


def main() -> None:
    """Write a fixture for each id named."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run", type=Path)
    parser.add_argument("ids", nargs="+")
    args = parser.parse_args()
    run: Path = args.run
    ids: list[str] = args.ids

    records: dict[str, dict[str, Any]] = {}
    for line in run.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        records[record["id"]] = record
    gold: list[dict[str, Any]] = json.loads(GOLD.read_text(encoding="utf-8"))
    questions = {item["id"]: item["question"] for item in gold}
    texts = {entry.path: entry.text for entry in load_corpus(DATA)}

    FIXTURES.mkdir(parents=True, exist_ok=True)
    for item_id in ids:
        record = records.get(item_id)
        if record is None:
            raise SystemExit(f"{item_id}: not in {run.name}")
        if record["config"]["level"] != 3:
            raise SystemExit(f"{item_id}: not a level 3 record, so it has no plan")
        if record["ruling"] is None:
            raise SystemExit(f"{item_id}: the ruling failed to parse")
        out = FIXTURES / f"{item_id}.json"
        data = fixture(record, questions[item_id], texts, run.name)
        out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
