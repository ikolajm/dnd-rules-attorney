"""Score each chunker by semantic retrieval and BM25, recall@k and all-cites@k.

Calls the live Ollama server and refuses any chunk past the model's context.
"""

import json
import time
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

from rules_attorney.bm25 import bm25_rank, build_index
from rules_attorney.chunk import (
    OVERLAP,
    WINDOW,
    Chunk,
    header_chunks,
    prepended_chunks,
    window_chunks,
)
from rules_attorney.corpus import load_corpus
from rules_attorney.metrics import all_cites_at_k, recall_at_k
from rules_attorney.provenance import commit
from rules_attorney.retrieve import (
    NOMIC,
    embed_documents,
    embed_query,
    ollama_embed,
    rank,
)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "srd-5.1"
GOLD = ROOT / "gold" / "gold.json"
RUNS = ROOT / "runs"
KS = [3, 5, 10, 20]
TOP = max(KS)
SIZE_K = 10
CHUNKERS = {
    "header": header_chunks,
    "prepended": prepended_chunks,
    "window": window_chunks,
}


def in_order(chunks: list[Chunk], labels: list[str]) -> list[Chunk]:
    """The chunks the labels name, in the labels' order."""
    return [chunks[int(label)] for label in labels]


def report(name: str, rankings: list[list[Chunk]], dev: list[dict[str, Any]]) -> None:
    """Print recall@k and all-cites@k at each k, and the top chunks' mean size."""
    ranked_paths = [[chunk.paths for chunk in ranked] for ranked in rankings]
    print(name)
    print("k   recall  all-cites")
    for k in KS:
        recall = sum(
            recall_at_k(ranked, item["cites"], k)
            for ranked, item in zip(ranked_paths, dev, strict=True)
        ) / len(dev)
        complete = sum(
            all_cites_at_k(ranked, item["cites"], k)
            for ranked, item in zip(ranked_paths, dev, strict=True)
        ) / len(dev)
        print(f"{k:<4}{recall:.3f}   {complete:.3f}")

    top = [chunk for ranked in rankings for chunk in ranked[:SIZE_K]]
    size = sum(len(chunk.text) for chunk in top) / len(top)
    print(f"mean characters, top {SIZE_K}: {size:.0f}")


def main() -> None:
    """For each chunker, embed and rank its chunks both ways, report and record each."""
    entries = load_corpus(DATA)
    items: list[dict[str, Any]] = json.loads(GOLD.read_text(encoding="utf-8"))
    dev = [item for item in items if item["split"] == "dev"]
    config: dict[str, Any] = {
        "embedder": NOMIC.model,
        "window": WINDOW,
        "overlap": OVERLAP,
        **commit(ROOT),
    }

    print(f"{len(entries)} entries, {len(dev)} dev items")
    embed = partial(ollama_embed, model=NOMIC.model)
    questions = [embed_query(item["question"], NOMIC, embed) for item in dev]

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"retrieval-{stamp}.jsonl"

    with out.open("w", encoding="utf-8") as file:
        for name, chunker in CHUNKERS.items():
            chunks = chunker(entries)
            labels = [str(i) for i in range(len(chunks))]
            texts = [chunk.text for chunk in chunks]
            start = time.perf_counter()
            matrix = embed_documents(texts, NOMIC, embed)
            seconds = time.perf_counter() - start
            semantic = [
                in_order(chunks, rank(vector, matrix, labels)) for vector in questions
            ]
            index = build_index(labels, texts)
            keyword = [
                in_order(chunks, bm25_rank(index, item["question"])) for item in dev
            ]

            print(f"{name}: {len(chunks)} chunks embedded in {seconds:.1f}s")

            for method, rankings in (("semantic", semantic), ("bm25", keyword)):
                report(f"{name} {method}", rankings, dev)

                for item, ranked in zip(dev, rankings, strict=True):
                    record = {
                        "id": item["id"],
                        "chunker": name,
                        "method": method,
                        "paths": [list(chunk.paths) for chunk in ranked[:TOP]],
                        "config": config,
                    }
                    file.write(json.dumps(record) + "\n")

    print(out)


if __name__ == "__main__":
    main()
