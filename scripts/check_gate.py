"""Runs the gate over a split's gold questions and the refusal set.

    python scripts/check_gate.py <model> [--split dev|test]

Gates with the model named, through the live Ollama server. The split is dev
unless test is named; the refusal set runs whole every time. Every gold
question should pass and every refusal be refused.
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from rules_attorney.answer import NUM_CTX, NUM_PREDICT, SEED, TEMPERATURE, THINK
from rules_attorney.gate import build_gate_prompt, ollama_gate, parse_gate
from rules_attorney.provenance import commit
from rules_attorney.split import SPLITS

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "gold" / "gold.json"
REFUSALS = ROOT / "gold" / "gate-refusals.json"
RUNS = ROOT / "runs"
# What the gate should return for each set's questions.
EXPECTED = {"gold": True, "refusal": False}


def main() -> None:
    """Gate each question and list the ones gated wrong."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model")
    parser.add_argument("--split", choices=SPLITS, default=SPLITS[0])
    args = parser.parse_args()
    model: str = args.model
    split: str = args.split
    items: list[dict[str, Any]] = json.loads(GOLD.read_text(encoding="utf-8"))
    gold = [item for item in items if item["split"] == split]
    # The refusal items carry no split, so the gold filter is not applied.
    refusals: list[dict[str, Any]] = json.loads(REFUSALS.read_text(encoding="utf-8"))
    questions = [("gold", item) for item in gold]
    questions += [("refusal", item) for item in refusals]

    source = commit(ROOT)
    config: dict[str, Any] = {
        "model": model,
        "split": split,
        "seed": SEED,
        "temperature": TEMPERATURE,
        "think": THINK,
        "num_ctx": NUM_CTX,
        "num_predict": NUM_PREDICT,
        "commit": source["commit"],
        "dirty": source["dirty"],
    }
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"gate-{stamp}-{split}-{model.replace(':', '-')}.jsonl"
    misses: list[dict[str, Any]] = []
    right = {"gold": 0, "refusal": 0}
    failures = 0

    with out.open("w", encoding="utf-8") as file:
        for kind, item in questions:
            start = time.perf_counter()
            reply = ollama_gate(build_gate_prompt(item["question"]), model=model)
            seconds = time.perf_counter() - start

            about_rules = parse_gate(reply)
            if about_rules is None:
                failures += 1
            # A reply that fails to parse is None, which matches neither
            # expectation, so it is a miss in either set.
            if about_rules is EXPECTED[kind]:
                right[kind] += 1
            else:
                misses.append({"kind": kind, "item": item, "reply": reply})

            record = {
                "id": item["id"],
                "kind": kind,
                "reply": reply,
                "about_rules": about_rules,
                "seconds": round(seconds, 2),
                "config": config,
            }
            file.write(json.dumps(record) + "\n")
            print(f"{item['id']}: {about_rules}")

    print(out)
    for miss in misses:
        print(f"miss, {miss['kind']}: {miss['item']['id']}")
        print(f"  question: {miss['item']['question']}")
        print(f"  reply: {miss['reply']!r}")
    print(f"gold passed: {right['gold']} / {len(gold)}")
    print(f"refusals refused: {right['refusal']} / {len(refusals)}")
    print(f"failed parses: {failures} / {len(questions)}")


if __name__ == "__main__":
    main()
