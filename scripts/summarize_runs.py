"""Summarizes runs and their judged files, tables them, or compares two runs' replies.

    python scripts/summarize_runs.py runs/<run>.jsonl [runs/<run>.jsonl ...]
    python scripts/summarize_runs.py --table runs/<run>.jsonl [runs/<run>.jsonl ...]
    python scripts/summarize_runs.py --compare runs/<old>.jsonl runs/<new>.jsonl

A run's judged file is found beside it, `<run>.judged-<judge>.jsonl`, and a
run judged more than once is refused rather than summarized from one judge
chosen silently. The flag is read as two rates, expected items flagged and
settled items flagged, a failed answer counted unflagged in its status. Cites
are resolved against the corpus, strict and once a leading `## ` is removed.

--table prints the published table, one markdown row per run in the order
given, from the same scores the summary prints.

--compare reports how many replies are identical byte for byte, item by item,
and names each item that differs.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from rules_attorney.corpus import load_corpus
from rules_attorney.table import Row, build_row, markdown_table

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


def score(records: list[dict[str, Any]], run: Path, known: set[str]) -> Row:
    """One run's scores, from its records and its one judged file."""
    judged = {record["id"]: record for record in load(judged_file(run))}
    return build_row(records, judged, known)


def summarize(run: Path, known: set[str]) -> None:
    """Print one run's config, agreement, flag rates, cites and timing."""
    records = load(run)
    row = score(records, run, known)
    cap = records[0]["config"].get("num_predict")
    print(run.name)
    print(f"  model {row.model} commit {row.commit[:7]} dirty {row.dirty} cap {cap}")
    print(f"  schema failures {len(row.failed)} of {row.items} {row.failed}")
    print(f"  verdict agreement {row.agreed} of {row.judged}")
    print(
        f"  flag expected {row.expected_flagged} of {row.expected},"
        f" settled {row.settled_flagged} of {row.settled}"
    )
    print(
        f"  cites {row.cites}, resolved strict {row.strict},"
        f" once unmarked {row.grounded}"
    )
    print(f"  seconds max {row.seconds_max:.1f}, total {row.seconds_total:.0f}")


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
    """Summarize the runs named, table them, or compare two."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("runs", nargs="+", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--compare", action="store_true")
    mode.add_argument("--table", action="store_true")
    args = parser.parse_args()

    if args.compare:
        if len(args.runs) != 2:
            parser.error("--compare takes exactly two runs")
        compare(*args.runs)
        return

    known = {entry.path for entry in load_corpus(DATA)}
    if args.table:
        rows = [score(load(run), run, known) for run in args.runs]
        try:
            print(markdown_table(rows))
        except ValueError as error:
            sys.exit(str(error))
        return
    for run in args.runs:
        summarize(run, known)


if __name__ == "__main__":
    main()
