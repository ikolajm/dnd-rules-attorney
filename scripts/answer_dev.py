"""Answers every dev item from its top 10 entries and writes one record per item.

Calls the live Ollama server.
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from rules_attorney.answer import (
    MODEL,
    NUM_CTX,
    SEED,
    TEMPERATURE,
    THINK,
    build_prompt,
    ollama_answer,
    parse_reply,
    unmarked,
    unresolved,
)
from rules_attorney.corpus import load_corpus
from rules_attorney.retrieve import MODEL as EMBED_MODEL
from rules_attorney.retrieve import (
    embed_documents,
    embed_query,
    ollama_embed,
    rank,
)

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
DATA = ROOT / "data" / "srd-5.1"
GOLD = ROOT / "gold" / "gold.json"
K = 10


def commit() -> dict[str, Any]:
    """The repo's HEAD commit, and whether the tree differs from it."""
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    return {"commit": head.stdout.strip(), "dirty": bool(status.stdout)}


def main() -> None:
    """Answer each dev item and write its record."""
    entries = load_corpus(DATA)
    by_path = {entry.path: entry for entry in entries}
    paths = [entry.path for entry in entries]
    known = set(paths)
    items: list[dict[str, Any]] = json.loads(GOLD.read_text(encoding="utf-8"))
    dev = [item for item in items if item["split"] == "dev"]
    matrix = embed_documents([entry.text for entry in entries], ollama_embed)
    source = commit()
    config: dict[str, Any] = {
        "model": MODEL,
        "embedder": EMBED_MODEL,
        "chunker": "header",
        "k": K,
        "seed": SEED,
        "temperature": TEMPERATURE,
        "think": THINK,
        "num_ctx": NUM_CTX,
        "commit": source["commit"],
        "dirty": source["dirty"],
    }

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"{stamp}-{MODEL.replace(':', '-')}.jsonl"
    failures = 0
    cites = 0
    resolved = 0
    grounded = 0

    with out.open("w", encoding="utf-8") as file:
        for item in dev:
            vector = embed_query(item["question"], ollama_embed)
            top = rank(vector, matrix, paths)[:K]
            prompt = build_prompt(item["question"], [by_path[path] for path in top])

            start = time.perf_counter()
            reply = ollama_answer(prompt)
            seconds = time.perf_counter() - start

            ruling = parse_reply(reply)
            if ruling is None:
                failures += 1
                missing: list[str] = []
            else:
                missing = unresolved(ruling.cites, known)
                cites += len(ruling.cites)
                resolved += len(ruling.cites) - len(missing)
                cleaned = unresolved(unmarked(ruling.cites), known)
                grounded += len(ruling.cites) - len(cleaned)

            record = {
                "id": item["id"],
                "retrieved": top,
                "reply": reply,
                "ruling": ruling.model_dump() if ruling is not None else None,
                "unresolved": missing,
                "seconds": round(seconds, 2),
                "config": config,
            }
            file.write(json.dumps(record) + "\n")

            status = "ok" if ruling is not None else "schema failure"
            print(f"{item['id']}: {status} in {seconds:.1f}s")

    print(out)
    print(f"schema failures: {failures} / {len(dev)}")
    print(f"cites resolved: {resolved} / {cites}")
    print(f"cites grounded: {grounded} / {cites}")


if __name__ == "__main__":
    main()
