"""Score semantic retrieval and BM25 on the dev items, recall@k and all-cites@k.

Calls the live Ollama server and refuses any entry past the model's context.
"""

import json
import time
from pathlib import Path
from typing import Any

from rules_attorney.bm25 import bm25_rank, build_index
from rules_attorney.corpus import load_corpus
from rules_attorney.metrics import all_cites_at_k, recall_at_k
from rules_attorney.retrieve import embed_documents, embed_query, ollama_embed, rank

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "srd-5.1"
GOLD = ROOT / "gold" / "gold.json"
KS = [3, 5, 10, 20]


def report(name: str, rankings: list[list[str]], dev: list[dict[str, Any]]) -> None:
    """Print recall@k and all-cites@k at each k for one set of rankings."""
    print(name)
    print("k   recall  all-cites")
    for k in KS:
        recall = sum(
            recall_at_k(ranked, item["cites"], k)
            for ranked, item in zip(rankings, dev, strict=True)
        ) / len(dev)
        complete = sum(
            all_cites_at_k(ranked, item["cites"], k)
            for ranked, item in zip(rankings, dev, strict=True)
        ) / len(dev)
        print(f"{k:<4}{recall:.3f}   {complete:.3f}")


def main() -> None:
    """Embed the corpus, rank each dev question both ways, and print both rows."""
    entries = load_corpus(DATA)
    paths = [entry.path for entry in entries]
    items: list[dict[str, Any]] = json.loads(GOLD.read_text(encoding="utf-8"))
    dev = [item for item in items if item["split"] == "dev"]

    start = time.perf_counter()
    matrix = embed_documents([entry.text for entry in entries], ollama_embed)
    seconds = time.perf_counter() - start

    rankings: list[list[str]] = []

    for item in dev:
        vector = embed_query(item["question"], ollama_embed)
        rankings.append(rank(vector, matrix, paths))

    index = build_index(paths, [entry.text for entry in entries])
    keyword_rankings = [bm25_rank(index, item["question"]) for item in dev]

    print(f"{len(entries)} entries embedded in {seconds:.1f}s, {len(dev)} dev items")

    report("semantic", rankings, dev)
    report("bm25", keyword_rankings, dev)


if __name__ == "__main__":
    main()
