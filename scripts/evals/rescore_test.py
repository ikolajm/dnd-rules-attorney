"""Rescores every published row on test at one clean commit, stopping on a failure.

    python scripts/evals/rescore_test.py [--dry-run]

Runs retrieval, the loops, every answer run and the floor, judges each, then
prints the tables, all in the order src/rules_attorney/evals/rescore.py gives.
Calls the live Ollama server and the Claude API. Refuses a dirty tree before
each step, and a HEAD that moved since the first. Each step's record is the
one new file it writes to runs/; a step writing none or more than one stops
the rescore. The records written are listed last, for results/test/.

--dry-run prints each step's command, the records named by their steps,
and runs nothing.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from rules_attorney.evals.provenance import commit
from rules_attorney.evals.rescore import (
    RescoreError,
    plan,
    refuse_moved,
    resolve,
    written,
)

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs"
SCRIPTS = ROOT / "scripts" / "evals"


def listing() -> set[Path]:
    """Every file in runs/, relative to the repo root."""
    if not RUNS.exists():
        return set()
    return {path.relative_to(ROOT) for path in RUNS.iterdir() if path.is_file()}


def main() -> None:
    """Run each step in order and list the records they wrote."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    steps = plan()
    if args.dry_run:
        named = {step.name: Path(f"<{step.name}>") for step in steps if step.writes}
        for step in steps:
            print(step.script, " ".join(resolve(step, named)))
        return

    start = commit(ROOT)
    records: dict[str, Path] = {}
    for number, step in enumerate(steps, 1):
        try:
            refuse_moved(start, commit(ROOT))
            command = [
                sys.executable,
                str(SCRIPTS / step.script),
                *resolve(step, records),
            ]
            print(f"\n[{number}/{len(steps)}] {step.name}", flush=True)
            before = listing()
            subprocess.run(command, check=True, cwd=ROOT)
            record = written(step, before, listing())
        except subprocess.CalledProcessError as error:
            sys.exit(f"stopped at {step.name}: exit {error.returncode}")
        except RescoreError as error:
            sys.exit(f"stopped: {error}")
        if record is not None:
            records[step.name] = record

    print(f"\nrecords at {start['commit'][:7]}:")
    for record in records.values():
        print(record.as_posix())


if __name__ == "__main__":
    main()
