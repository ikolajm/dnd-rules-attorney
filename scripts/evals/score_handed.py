"""Scores the ten each answer record retrieved, one report per run.

    python scripts/evals/score_handed.py runs/<run>.jsonl [runs/<run>.jsonl ...]

Each record is scored against the cites of the gold item with its id. A run
recorded on a dirty tree is refused.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from rules_attorney.evals.metrics import all_cites_at_k, recall_at_k

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "gold" / "gold.json"
KS = [3, 5, 10]


def report(
    name: str, rankings: list[list[str]], chosen: list[dict[str, Any]], ks: list[int]
) -> None:
    """Print recall@k and all-cites@k at each k for one order."""
    ranked_paths: list[list[tuple[str, ...]]] = [
        [(path,) for path in ranking] for ranking in rankings
    ]
    print(name)
    print("k   recall  all-cites")

    for k in ks:
        recall = sum(
            recall_at_k(ranked, item["cites"], k)
            for ranked, item in zip(ranked_paths, chosen, strict=True)
        ) / len(chosen)
        complete = sum(
            all_cites_at_k(ranked, item["cites"], k)
            for ranked, item in zip(ranked_paths, chosen, strict=True)
        ) / len(chosen)
        print(f"{k:<4}{recall:.3f}   {complete:.3f}")


def main() -> None:
    """Score each run's retrieved tens against the gold cites."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("runs", nargs="+", type=Path)
    args = parser.parse_args()
    runs: list[Path] = args.runs
    items: list[dict[str, Any]] = json.loads(GOLD.read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in items}
    for run in runs:
        records = [json.loads(line) for line in run.open(encoding="utf-8")]
        if any(record["config"]["dirty"] for record in records):
            parser.error(f"{run.name} was recorded on a dirty tree")
        rankings = [record["retrieved"] for record in records]
        chosen = [by_id[record["id"]] for record in records]
        report(run.name, rankings, chosen, KS)


if __name__ == "__main__":
    main()
