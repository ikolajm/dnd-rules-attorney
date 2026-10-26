"""Score each embedder on header entries by semantic retrieval, BM25 and their fusion.

Calls the live Ollama server and refuses any chunk past the model's context.
"""

import json
import time
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any, TextIO

from rules_attorney.bm25 import bm25_rank, build_index
from rules_attorney.chunk import Chunk, header_chunks
from rules_attorney.corpus import load_corpus
from rules_attorney.fusion import fuse
from rules_attorney.metrics import all_cites_at_k, recall_at_k
from rules_attorney.provenance import commit
from rules_attorney.retrieve import (
    EMBEDDERS,
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


def write_records(
    file: TextIO,
    dev: list[dict[str, Any]],
    rankings: list[list[Chunk]],
    *,
    embedder: str | None,
    method: str,
    config: dict[str, Any],
) -> None:
    """One record per dev item: its top chunks' paths and the method that ranked it."""
    for item, ranked in zip(dev, rankings, strict=True):
        record = {
            "id": item["id"],
            "embedder": embedder,
            "method": method,
            "paths": [list(chunk.paths) for chunk in ranked[:TOP]],
            "config": config,
        }
        file.write(json.dumps(record) + "\n")


def main() -> None:
    """Rank header entries by BM25 once and by each embedder, alone and fused."""
    entries = load_corpus(DATA)
    items: list[dict[str, Any]] = json.loads(GOLD.read_text(encoding="utf-8"))
    dev = [item for item in items if item["split"] == "dev"]
    config: dict[str, Any] = {"chunker": "header", **commit(ROOT)}

    print(f"{len(entries)} entries, {len(dev)} dev items")

    chunks = header_chunks(entries)
    labels = [str(i) for i in range(len(chunks))]
    texts = [chunk.text for chunk in chunks]

    # BM25 does not depend on the embedder, so it is ranked once.
    index = build_index(labels, texts)
    keyword_labels = [bm25_rank(index, item["question"]) for item in dev]
    keyword = [in_order(chunks, ranked) for ranked in keyword_labels]

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"retrieval-{stamp}.jsonl"

    with out.open("w", encoding="utf-8") as file:
        # Written once, outside the loop: BM25 is the same for every embedder.
        report("bm25", keyword, dev)
        write_records(file, dev, keyword, embedder=None, method="bm25", config=config)

        for embedder in EMBEDDERS:
            # Questions are embedded inside the loop: a query vector belongs
            # to the model and prefix that made it.
            embed = partial(ollama_embed, model=embedder.model)
            questions = [embed_query(item["question"], embedder, embed) for item in dev]
            start = time.perf_counter()
            matrix = embed_documents(texts, embedder, embed)
            seconds = time.perf_counter() - start
            semantic_labels = [rank(vector, matrix, labels) for vector in questions]
            semantic = [in_order(chunks, ranked) for ranked in semantic_labels]

            fused_labels = [
                fuse([meaning, words])
                for meaning, words in zip(semantic_labels, keyword_labels, strict=True)
            ]
            fused = [in_order(chunks, ranked) for ranked in fused_labels]

            print(f"{embedder.model}: {len(chunks)} chunks embedded in {seconds:.1f}s")
            for method, rankings in (("semantic", semantic), ("fused", fused)):
                report(f"{embedder.model} {method}", rankings, dev)
                write_records(
                    file,
                    dev,
                    rankings,
                    embedder=embedder.model,
                    method=method,
                    config=config,
                )

    print(out)


if __name__ == "__main__":
    main()
