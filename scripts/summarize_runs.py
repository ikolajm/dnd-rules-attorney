"""Summarizes dev runs and their judged files, or compares two runs' replies.

    python scripts/summarize_runs.py runs/<run>.jsonl [runs/<run>.jsonl ...]
    python scripts/summarize_runs.py --compare runs/<old>.jsonl runs/<new>.jsonl

A run's judged file is found beside it, `<run>.judged-<judge>.jsonl`, and a
run judged more than once is refused rather than summarized from one judge
chosen silently. The flag is read as two rates, expected items flagged and
settled items flagged, a failed answer counted unflagged in its status. Cites
are resolved against the corpus, strict and once a leading `## ` is removed.

--compare reports how many replies are identical byte for byte, item by item,
and names each item that differs.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from rules_attorney.answer import unmarked
from rules_attorney.corpus import load_corpus

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "srd-5.1"


def load(path: Path) -> list[dict[str, Any]]:
    """The records of a JSONL file."""
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def judged_file(run: Path) -> Path:
    """The one judged file beside a run."""
    found = sorted(run.parent.glob(f"{run.stem}.judged-*.jsonl"))
    if len(found) != 1:
        sys.exit(f"{run.name}: expected one judged file, found {len(found)}")
    return found[0]


def summarize(run: Path, known: set[str]) -> None:
    """Print one run's config, agreement, flag rates, cites and timing."""
    records = load(run)
    judged = {record["id"]: record for record in load(judged_file(run))}
    config = records[0]["config"]
    ok = [record for record in records if record["ruling"] is not None]
    failed = [record["id"] for record in records if record["ruling"] is None]

    sent = [j for j in judged.values() if j["judged"]]
    agree = sum(1 for j in sent if j["agrees"])

    def flagged(status_settled: bool) -> tuple[int, int]:
        rows = [
            r
            for r in records
            if (judged[r["id"]]["status"] == "settled") == status_settled
        ]
        hits = sum(
            1 for r in rows if r["ruling"] is not None and r["ruling"]["ambiguous"]
        )
        return hits, len(rows)

    cites = [cite for record in ok for cite in record["ruling"]["cites"]]
    strict = sum(1 for cite in cites if cite in known)
    grounded = sum(1 for cite in unmarked(cites) if cite in known)
    integers = sum(1 for record in ok if isinstance(record["ruling"]["verdict"], int))
    seconds = [record["seconds"] for record in records]

    print(run.name)
    print(
        f"  model {config['model']} commit {config['commit'][:7]}"
        f" dirty {config['dirty']} cap {config.get('num_predict')}"
    )
    print(f"  schema failures {len(failed)} of {len(records)} {failed}")
    print(f"  verdict agreement {agree} of {len(sent)}")
    print(
        "  flag expected {} of {}, settled {} of {}".format(
            *flagged(False), *flagged(True)
        )
    )
    print(f"  cites {len(cites)}, resolved strict {strict}, once unmarked {grounded}")
    print(f"  integer verdicts {integers}")
    print(f"  seconds max {max(seconds):.1f}, total {sum(seconds):.0f}")


def compare(old: Path, new: Path) -> None:
    """Print how many replies two runs share byte for byte, naming each that differs."""
    before = {record["id"]: record["reply"] for record in load(old)}
    after = {record["id"]: record["reply"] for record in load(new)}
    if before.keys() != after.keys():
        sys.exit("the two runs answer different items")
    differ = [item for item in before if before[item] != after[item]]
    print(f"replies identical: {len(before) - len(differ)} of {len(before)}")
    for item in differ:
        print(f"  differs: {item}")


def main() -> None:
    """Summarize the runs named, or compare two."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args()

    if args.compare:
        if len(args.runs) != 2:
            parser.error("--compare takes exactly two runs")
        compare(*args.runs)
        return

    known = {entry.path for entry in load_corpus(DATA)}
    for run in args.runs:
        summarize(run, known)


if __name__ == "__main__":
    main()
