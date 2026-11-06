"""Rerank level 1's top entries for every item of a split, and score both orders.

    python scripts/evals/eval_rerank.py [--split dev|test]

Embeds through the live Ollama server and reranks with the cross-encoder.
The split is dev unless test is named.
"""

import argparse
import json
import time
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

from rules_attorney.corpus import load_corpus
from rules_attorney.evals.metrics import all_cites_at_k, recall_at_k
from rules_attorney.evals.provenance import commit
from rules_attorney.evals.split import SPLITS
from rules_attorney.rerank import DEPTH, RERANKER, cross_encoder, fused_order, rerank
from rules_attorney.retrieve import (
    NOMIC,
    embed_documents,
    embed_query,
    ollama_embed,
    rank,
)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "srd-5.1"
GOLD = ROOT / "gold" / "gold.json"
RUNS = ROOT / "runs"
KS = [3, 5, 10, 20]
EMBEDDER = NOMIC


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
    """Rank each item of the split, rerank its top entries, and score both."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--split", choices=SPLITS, default=SPLITS[0])
    split: str = parser.parse_args().split
    entries = load_corpus(DATA)
    paths = [entry.path for entry in entries]
    by_path = {entry.path: entry for entry in entries}
    items: list[dict[str, Any]] = json.loads(GOLD.read_text(encoding="utf-8"))
    chosen = [item for item in items if item["split"] == split]
    embed = partial(ollama_embed, model=EMBEDDER.model)
    matrix = embed_documents([entry.text for entry in entries], EMBEDDER, embed)
    score = cross_encoder(RERANKER)
    source = commit(ROOT)
    config: dict[str, Any] = {
        "split": split,
        "embedder": EMBEDDER.model,
        "reranker": RERANKER,
        "depth": DEPTH,
        "commit": source["commit"],
        "dirty": source["dirty"],
    }
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"rerank-{stamp}-{split}.jsonl"
    befores: list[list[str]] = []
    afters: list[list[str]] = []
    fused_orders: list[list[str]] = []
    seconds_total = 0.0

    with out.open("w", encoding="utf-8") as file:
        for item in chosen:
            vector = embed_query(item["question"], EMBEDDER, embed)
            before = rank(vector, matrix, paths)[:DEPTH]
            start = time.perf_counter()
            after = rerank(item["question"], [by_path[path] for path in before], score)
            seconds = time.perf_counter() - start
            seconds_total += seconds
            fused = fused_order(after, before)
            befores.append(before)
            afters.append(after)
            fused_orders.append(fused)
            record: dict[str, Any] = {
                "id": item["id"],
                "before": before,
                "after": after,
                "fused": fused,
                "seconds": round(seconds, 2),
                "config": config,
            }
            file.write(json.dumps(record) + "\n")
            print(f"{item['id']}: {seconds:.2f}s")

    print(out)
    report("level 1", befores, chosen, [*KS, DEPTH])
    report(f"level 1 reranked by {RERANKER}", afters, chosen, KS)
    report(f"level 1 fused with {RERANKER}", fused_orders, chosen, KS)
    print(f"rerank seconds: {seconds_total:.1f}")


if __name__ == "__main__":
    main()
