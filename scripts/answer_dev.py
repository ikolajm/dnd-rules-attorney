"""Answers every dev item from its top 10 entries and writes one record per item.

Calls the live Ollama server with the model named as its one argument.
"""

import json
import sys
import time
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

from rules_attorney.answer import (
    NUM_CTX,
    SEED,
    TEMPERATURE,
    THINK,
    Ruling,
    build_prompt,
    ollama_answer,
    parse_reply,
    unmarked,
    unresolved,
)
from rules_attorney.corpus import load_corpus
from rules_attorney.provenance import commit
from rules_attorney.retrieve import (
    NOMIC,
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
EMBEDDER = NOMIC


def main() -> None:
    """Answer each dev item and write its record."""
    model = sys.argv[1]
    entries = load_corpus(DATA)
    by_path = {entry.path: entry for entry in entries}
    paths = [entry.path for entry in entries]
    known = set(paths)
    items: list[dict[str, Any]] = json.loads(GOLD.read_text(encoding="utf-8"))
    dev = [item for item in items if item["split"] == "dev"]
    embed = partial(ollama_embed, model=EMBEDDER.model)
    matrix = embed_documents([entry.text for entry in entries], EMBEDDER, embed)
    source = commit(ROOT)
    config: dict[str, Any] = {
        "model": model,
        "embedder": EMBEDDER.model,
        "chunker": "header",
        "k": K,
        "seed": SEED,
        "temperature": TEMPERATURE,
        "think": THINK,
        "num_ctx": NUM_CTX,
        "fields": list(Ruling.model_fields),
        "commit": source["commit"],
        "dirty": source["dirty"],
    }

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"{stamp}-{model.replace(':', '-')}.jsonl"
    failures = 0
    cites = 0
    resolved = 0
    grounded = 0

    with out.open("w", encoding="utf-8") as file:
        for item in dev:
            vector = embed_query(item["question"], EMBEDDER, embed)
            top = rank(vector, matrix, paths)[:K]
            prompt = build_prompt(item["question"], [by_path[path] for path in top])

            start = time.perf_counter()
            reply = ollama_answer(prompt, model=model)
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
