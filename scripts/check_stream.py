"""Compares the served stream for gold items with their measured level 3 records.

    python scripts/check_stream.py <id> [<id> ...] [--run <run file>] [--url <url>]

Posts each item's question to the running server and reads its events,
printing when each lands. For a gold item, the sub-questions, the entries in
order and the ruling must each equal its record in the run file, which is
level 3's dev run unless another is named. An item from the gate's refusal
set must end at the gate, refused.
"""

import argparse
import json
import sys
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "gold" / "gold.json"
REFUSALS = ROOT / "gold" / "gate-refusals.json"
RUN = ROOT / "runs" / "20261028-152008-dev-level3-qwen3.5-9b.jsonl"
URL = "http://127.0.0.1:8000/ask"


def events(lines: Iterator[str]) -> Iterator[tuple[str, Any]]:
    """Each event's name and its decoded data, from the stream's lines."""
    name = ""
    data: list[str] = []
    for line in lines:
        if line.startswith(":"):
            # A keepalive comment, which FastAPI sends on a quiet stream.
            continue
        if line.startswith("event: "):
            name = line.removeprefix("event: ")
        elif line.startswith("data: "):
            data.append(line.removeprefix("data: "))
        elif not line and data:
            # A blank line ends the event.
            yield name, json.loads("\n".join(data))
            name, data = "", []


def stream(url: str, question: str) -> dict[str, Any]:
    """The events of one question's run, keyed by name, each timed as it lands."""
    body = json.dumps({"question": question}).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    start = time.perf_counter()
    served: dict[str, Any] = {}
    with urllib.request.urlopen(request) as response:
        lines = (raw.decode("utf-8").rstrip("\r\n") for raw in response)
        for name, data in events(lines):
            served[name] = data
            # Printed as each lands, so a run stopped by hand shows how far
            # it got, and the next run's gate shows whether the stop
            # reached Ollama.
            print(f"  {name} at {time.perf_counter() - start:.2f}s", flush=True)
    return served


def main() -> None:
    """Stream each item named and list every field that differs from its record."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ids", nargs="+")
    parser.add_argument("--run", type=Path, default=RUN)
    parser.add_argument("--url", default=URL)
    args = parser.parse_args()
    ids: list[str] = args.ids
    run: Path = args.run
    url: str = args.url

    records: dict[str, dict[str, Any]] = {}
    for line in run.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        records[record["id"]] = record
    gold: list[dict[str, Any]] = json.loads(GOLD.read_text(encoding="utf-8"))
    questions = {item["id"]: item["question"] for item in gold}
    refusals: list[dict[str, Any]] = json.loads(REFUSALS.read_text(encoding="utf-8"))
    refusal_questions = {item["id"]: item["question"] for item in refusals}

    differing = 0
    for item_id in ids:
        if item_id in refusal_questions:
            # A refusal has no record: it should end at the gate.
            served = stream(url, refusal_questions[item_id])
            refused = list(served) == ["gate"] and not served["gate"]["about_rules"]
            if not refused:
                differing += 1
            print(f"{item_id}: {'refused' if refused else 'not refused'}")
            continue
        record = records.get(item_id)
        if record is None:
            sys.exit(f"{item_id}: not in {run.name}")
        if record["config"]["level"] != 3:
            sys.exit(f"{item_id}: not a level 3 record, so it has no plan")
        served = stream(url, questions[item_id])
        if "error" in served:
            sys.exit(f"{item_id}: the run ended in {served['error']['reason']}")

        fields = {
            "sub_questions": (
                served["plan"]["sub_questions"],
                record["sub_questions"],
            ),
            "entries": (
                [entry["path"] for entry in served["entries"]["entries"]],
                record["retrieved"],
            ),
            "ruling": (served.get("ruling"), record["ruling"]),
        }
        moved = [field for field, (got, want) in fields.items() if got != want]
        if moved:
            differing += 1
        print(f"{item_id}: {'same' if not moved else 'differs in ' + ', '.join(moved)}")
        for field in moved:
            got, want = fields[field]
            print(f"  {field}, served:   {json.dumps(got)}")
            print(f"  {field}, measured: {json.dumps(want)}")

    print(f"as expected: {len(ids) - differing} / {len(ids)}")


if __name__ == "__main__":
    main()
