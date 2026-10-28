"""Ranks every item of a split by its question and its sub-questions, merged.

    python scripts/eval_multihop.py <model> [--split dev|test]

Plans with the model named, through the live Ollama server. The split is dev
unless test is named.
"""

import argparse
import json
import time
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

from rules_attorney.answer import NUM_CTX, NUM_PREDICT, SEED, TEMPERATURE, THINK
from rules_attorney.corpus import load_corpus
from rules_attorney.metrics import all_cites_at_k, recall_at_k
from rules_attorney.multihop import (
    build_plan_prompt,
    merged_ranking,
    ollama_plan,
    parse_plan,
)
from rules_attorney.provenance import commit
from rules_attorney.retrieve import (
    NOMIC,
    embed_documents,
    embed_query,
    ollama_embed,
    rank,
)
from rules_attorney.split import SPLITS

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "srd-5.1"
GOLD = ROOT / "gold" / "gold.json"
RUNS = ROOT / "runs"
KS = [3, 5, 10, 20]
K = 10
TOP = max(KS)
EMBEDDER = NOMIC


def main() -> None:
    """Plan each item of the split and merge its rankings."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model")
    parser.add_argument("--split", choices=SPLITS, default=SPLITS[0])
    args = parser.parse_args()
    model: str = args.model
    split: str = args.split
    entries = load_corpus(DATA)
    paths = [entry.path for entry in entries]
    items: list[dict[str, Any]] = json.loads(GOLD.read_text(encoding="utf-8"))
    chosen = [item for item in items if item["split"] == split]
    embed = partial(ollama_embed, model=EMBEDDER.model)
    matrix = embed_documents([entry.text for entry in entries], EMBEDDER, embed)
    source = commit(ROOT)
    config: dict[str, Any] = {
        "model": model,
        "split": split,
        "embedder": EMBEDDER.model,
        "k": K,
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
    out = RUNS / f"multihop-{stamp}-{split}-{model.replace(':', '-')}.jsonl"
    merged_rankings: list[list[str]] = []
    failures = 0

    with out.open("w", encoding="utf-8") as file:
        for item in chosen:
            vector = embed_query(item["question"], EMBEDDER, embed)
            ranking = rank(vector, matrix, paths)

            start = time.perf_counter()
            reply = ollama_plan(build_plan_prompt(item["question"]), model=model)
            seconds = time.perf_counter() - start

            plan = parse_plan(reply)
            if plan is None:
                failures += 1
            sub_questions = plan or []
            sub_rankings = [
                rank(embed_query(sub, EMBEDDER, embed), matrix, paths)
                for sub in sub_questions
            ]
            merged = merged_ranking(ranking, sub_rankings)
            merged_rankings.append(merged)

            record = {
                "id": item["id"],
                "reply": reply,
                "sub_questions": sub_questions,
                "seconds": round(seconds, 2),
                "merged": merged[:TOP],
                "config": config,
            }
            file.write(json.dumps(record) + "\n")
            print(f"{item['id']}: {len(sub_questions)} sub-questions")

    print(out)
    ranked_paths: list[list[tuple[str, ...]]] = [
        [(path,) for path in merged] for merged in merged_rankings
    ]
    print("k   recall  all-cites")
    for k in KS:
        recall = sum(
            recall_at_k(ranked, item["cites"], k)
            for ranked, item in zip(ranked_paths, chosen, strict=True)
        ) / len(chosen)
        complete = sum(
            all_cites_at_k(ranked, item["cites"], k)
            for ranked, item in zip(ranked_paths, chosen, strict=True)
        ) / len(chosen)
        print(f"{k:<4}{recall:.3f}   {complete:.3f}")

    print(f"failed plans: {failures} / {len(chosen)}")


if __name__ == "__main__":
    main()
