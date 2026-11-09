"""Rescores every published row on test at one clean commit, stopping on a failure.

    python scripts/evals/rescore_published.py [--dry-run]

Runs retrieval, the loops, every answer run and the floor, judges each, then
prints the tables, all in the order src/rules_attorney/evals/rescore.py gives,
the local runs before the hosted model's. Calls the live Ollama server and the
Claude API. Refuses a dirty tree before each step, and a HEAD that moved since
the first. Each step's record is the one file it writes or rewrites in runs/;
a step writing none or more than one stops the rescore.

Each record is noted in runs/rescore/<commit>.json as its step finishes, and a
rescore started again at the same commit skips the steps noted there, so a
failure late in the run costs only the step that failed. Delete the manifest
to start over. The records are listed last, for results/test/.

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
    manifest_text,
    plan,
    read_manifest,
    refuse_moved,
    resolve,
    written,
)

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs"
MANIFESTS = RUNS / "rescore"
SCRIPTS = ROOT / "scripts" / "evals"


def listing() -> dict[Path, int]:
    """Every file in runs/, relative to the repo root, with its modified time.

    The manifests sit in a folder of their own, so a listing never counts one.
    """
    if not RUNS.exists():
        return {}
    return {
        path.relative_to(ROOT): path.stat().st_mtime_ns
        for path in RUNS.iterdir()
        if path.is_file()
    }


def main() -> None:
    """Run each step not yet done at this commit, and list the records."""
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
    manifest = MANIFESTS / f"{start['commit']}.json"
    records: dict[str, Path] = {}
    try:
        refuse_moved(start, start)
        if manifest.exists():
            text = manifest.read_text(encoding="utf-8")
            records = read_manifest(text, start["commit"], set(listing()))
            print(f"resuming: {len(records)} steps done, from {manifest.name}")
    except RescoreError as error:
        sys.exit(f"stopped: {error}")

    for number, step in enumerate(steps, 1):
        if step.name in records:
            continue
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
            MANIFESTS.mkdir(parents=True, exist_ok=True)
            manifest.write_text(
                manifest_text(start["commit"], records), encoding="utf-8"
            )

    print(f"\nrecords at {start['commit'][:7]}:")
    for record in records.values():
        print(record.as_posix())


if __name__ == "__main__":
    main()
