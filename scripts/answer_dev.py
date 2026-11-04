"""Answers every item of a split from its top 10 entries, one record per item.

    python scripts/answer_dev.py <model> [--split dev|test] [--level 1|3]
        [--rerank] [--lookup] [--loop-records <path>]

Answers with the model named: through the Claude API when its name starts
with claude-, through the live Ollama server otherwise. The split is dev
unless test is named. Level 3 plans sub-questions with the same model and
answers from the merged ranking's top 10.

--rerank reorders level 1's top 30 with the cross-encoder
and answers from its fusion with level 1's order.

--lookup answers from the records the question names, linked ahead of level
1's order.

--loop-records answers from the ten each item's record from
scripts/eval_agentic.py handed over, without running the loop again.
"""

import argparse
import json
import time
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

from rules_attorney.agentic import loop_handed
from rules_attorney.answer import (
    NUM_CTX,
    NUM_PREDICT,
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
from rules_attorney.hosted import (
    EFFORT,
    MAX_TOKENS,
    MODEL_PREFIX,
    claude_answer,
    claude_plan,
)
from rules_attorney.judge import reply_text
from rules_attorney.lookup import KINDS, links, lookup_order, name_index
from rules_attorney.multihop import (
    build_plan_prompt,
    merged_ranking,
    ollama_plan,
    parse_plan,
)
from rules_attorney.provenance import commit
from rules_attorney.rerank import (
    DEPTH,
    RERANKER,
    Score,
    cross_encoder,
    fused_order,
    rerank,
)
from rules_attorney.retrieve import (
    NOMIC,
    embed_documents,
    embed_query,
    ollama_embed,
    rank,
)
from rules_attorney.split import SPLITS

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
DATA = ROOT / "data" / "srd-5.1"
GOLD = ROOT / "gold" / "gold.json"
K = 10
EMBEDDER = NOMIC


def main() -> None:
    """Answer each item of the split and write its record."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model")
    parser.add_argument("--split", choices=SPLITS, default=SPLITS[0])
    parser.add_argument("--level", type=int, choices=[1, 3], default=1)
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument("--lookup", action="store_true")
    parser.add_argument("--loop-records", type=Path)
    args = parser.parse_args()
    model: str = args.model
    split: str = args.split
    level: int = args.level
    reranking: bool = args.rerank
    looking_up: bool = args.lookup
    loop_records: Path | None = args.loop_records
    if looking_up and reranking:
        parser.error("--lookup and --rerank are separate stages; run one at a time")
    if reranking and level == 3:
        parser.error("--rerank is measured on level 1 only")
    if looking_up and level == 3:
        parser.error("--lookup is measured on level 1 only")
    if loop_records is not None and (reranking or looking_up):
        parser.error("--loop-records is a stage of its own; run one stage at a time")
    if loop_records is not None and level == 3:
        parser.error("--loop-records answers in place of level 1's ten")
    hosted = model.startswith(MODEL_PREFIX)
    entries = load_corpus(DATA)
    by_path = {entry.path: entry for entry in entries}
    paths = [entry.path for entry in entries]
    known = set(paths)
    items: list[dict[str, Any]] = json.loads(GOLD.read_text(encoding="utf-8"))
    chosen = [item for item in items if item["split"] == split]
    handed: dict[str, list[str]] | None = None
    loop_commit: str | None = None
    if loop_records is not None:
        # Refused here, before the embeddings run or any model is called.
        lines = loop_records.read_text(encoding="utf-8").splitlines()
        loop = [json.loads(line) for line in lines]
        try:
            handed = loop_handed(loop, split, model, [item["id"] for item in chosen])
        except ValueError as error:
            parser.error(str(error))
        # loop_handed refused mixed commits, so the first record's is the run's.
        loop_commit = loop[0]["config"]["commit"]
    embed = partial(ollama_embed, model=EMBEDDER.model)
    matrix = embed_documents([entry.text for entry in entries], EMBEDDER, embed)
    score: Score | None = cross_encoder(RERANKER) if reranking else None
    index: dict[str, list[str]] | None = (
        name_index(entries, KINDS) if looking_up else None
    )
    source = commit(ROOT)
    config: dict[str, Any] = {
        "model": model,
        "split": split,
        "level": level,
        "embedder": EMBEDDER.model,
        "chunker": "header",
        "k": K,
        "reranker": RERANKER if reranking else None,
        "depth": DEPTH if reranking else None,
        "lookup": list(KINDS) if looking_up else None,
        "loop": loop_records.name if loop_records is not None else None,
        "loop_commit": loop_commit,
        "fields": list(Ruling.model_fields),
        "commit": source["commit"],
        "dirty": source["dirty"],
    }
    if hosted:
        # Opus 5.5 takes no seed or temperature and cannot turn thinking off.
        config.update({"effort": EFFORT, "max_tokens": MAX_TOKENS, "think": "adaptive"})
    else:
        config.update(
            {
                "seed": SEED,
                "temperature": TEMPERATURE,
                "think": THINK,
                "num_ctx": NUM_CTX,
                "num_predict": NUM_PREDICT,
            }
        )

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    marker = "-level3" if level == 3 else ""
    if reranking:
        marker = "-rerank"
    if looking_up:
        marker = "-lookup"
    if loop_records is not None:
        marker = "-loop"
    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"{stamp}-{split}{marker}-{model.replace(':', '-')}.jsonl"
    failures = 0
    plan_failures = 0
    cites = 0
    resolved = 0
    grounded = 0

    with out.open("w", encoding="utf-8") as file:
        for item in chosen:
            vector = embed_query(item["question"], EMBEDDER, embed)
            ranking = rank(vector, matrix, paths)
            planned: dict[str, Any] = {}
            if level == 3:
                plan_start = time.perf_counter()
                plan_prompt = build_plan_prompt(item["question"])
                plan_usage: dict[str, Any] = {}
                if hosted:
                    plan_message = claude_plan(plan_prompt, model=model)
                    plan_reply = reply_text(plan_message)
                    plan_usage = {
                        "plan_input_tokens": plan_message.usage.input_tokens,
                        "plan_output_tokens": plan_message.usage.output_tokens,
                    }
                else:
                    plan_reply = ollama_plan(plan_prompt, model=model)
                plan_seconds = time.perf_counter() - plan_start
                plan = parse_plan(plan_reply)
                if plan is None:
                    plan_failures += 1
                sub_questions = plan or []
                sub_rankings = [
                    rank(embed_query(sub, EMBEDDER, embed), matrix, paths)
                    for sub in sub_questions
                ]
                ranking = merged_ranking(ranking, sub_rankings)
                planned = {
                    "plan_reply": plan_reply,
                    "sub_questions": sub_questions,
                    "plan_seconds": round(plan_seconds, 2),
                    **plan_usage,
                }
            reordered: dict[str, Any] = {}
            if score is not None:
                rerank_start = time.perf_counter()
                candidates = ranking[:DEPTH]
                order = rerank(
                    item["question"], [by_path[path] for path in candidates], score
                )
                ranking = fused_order(order, candidates)
                reordered = {
                    "rerank_seconds": round(time.perf_counter() - rerank_start, 2)
                }
            looked_up: dict[str, Any] = {}
            if index is not None:
                named = links(item["question"], index)
                ranking = lookup_order(named, ranking, K)
                looked_up = {"links": named}
            if handed is not None:
                # The ten the loop's record handed over, in place of level 1's.
                ranking = handed[item["id"]]
            top = ranking[:K]
            prompt = build_prompt(item["question"], [by_path[path] for path in top])

            start = time.perf_counter()
            usage: dict[str, Any] = {}
            if hosted:
                message = claude_answer(prompt, model=model)
                reply = reply_text(message)
                # The stop reason shows a refusal or a hit cap, and the
                # tokens give the run's measured cost.
                usage = {
                    "stop": message.stop_reason,
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                }
            else:
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
                **usage,
                **planned,
                **reordered,
                **looked_up,
                "config": config,
            }
            file.write(json.dumps(record) + "\n")

            status = "ok" if ruling is not None else "schema failure"
            print(f"{item['id']}: {status} in {seconds:.1f}s")

    print(out)
    print(f"schema failures: {failures} / {len(chosen)}")
    if level == 3:
        print(f"failed plans: {plan_failures} / {len(chosen)}")
    print(f"cites resolved: {resolved} / {cites}")
    print(f"cites grounded: {grounded} / {cites}")


if __name__ == "__main__":
    main()
