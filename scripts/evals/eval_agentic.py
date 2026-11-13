"""Runs the agentic loop on every item of a split and scores the ten it hands over.

    python scripts/evals/eval_agentic.py <model> [--split dev|test] [--records <path>]

Searches with the model named, through the live Ollama server, or through the
Claude API when its name starts with claude-. The split is dev unless test is
named.

--records prints the same report from records this script already wrote, with
no search and no model call, refusing records of another split or model, from
a dirty tree or more than one commit, or missing an item.
"""

import argparse
import json
import time
from dataclasses import asdict
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

from rules_attorney.agentic import (
    CALL_CAP,
    Backend,
    OllamaBackend,
    Trace,
    build_dispatch,
    hand_over,
    loop_handed,
    run_loop,
)
from rules_attorney.answer import NUM_CTX, NUM_PREDICT, SEED, TEMPERATURE, THINK
from rules_attorney.corpus import load_corpus
from rules_attorney.evals.metrics import all_cites_at_k, report
from rules_attorney.evals.provenance import commit
from rules_attorney.evals.split import SPLITS
from rules_attorney.hosted import EFFORT, MAX_TOKENS, MODEL_PREFIX, ClaudeBackend
from rules_attorney.lookup import KINDS, links, lookup_order, name_index
from rules_attorney.retrieve import (
    NOMIC,
    embed_documents,
    embed_query,
    ollama_embed,
    rank,
)
from rules_attorney.tools import NO_RECORD, SEARCH_K

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "srd-5.1"
GOLD = ROOT / "gold" / "gold.json"
RUNS = ROOT / "runs"
K = 10
# How much of each ranking a record keeps, as eval_retrieval.py keeps.
TOP = 20
EMBEDDER = NOMIC
# The ten is all the loop hands over, so the report stops there.
KS = [3, 5, 10]
# The dev items that turn on a name after a colon, which the matcher leaves to
# the lookup tool: Fighting Style: Dueling and the Spellcasting features.
COLON_ITEMS = (
    "dueling-with-shield",
    "dueling-thrown-dagger",
    "two-weapon-style-modifier",
    "wizard-ritual-unprepared",
    "cleric-ritual-unprepared",
    "copy-fireball-too-early",
)


def calls_of(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Every call of a record's trace, across its turns, in order."""
    return [call for turn in record["trace"]["turns"] for call in turn["calls"]]


def ratio(part: int, whole: int) -> str:
    """The share to three places, or a dash when there is nothing to divide."""
    return f"{part / whole:.3f}" if whole else "-"


def trace_record(trace: Trace) -> dict[str, Any]:
    """The trace as JSON-ready dicts, each call's ranking cut to TOP."""
    data = asdict(trace)
    for turn in data["turns"]:
        for call in turn["calls"]:
            # A search's ranking is the whole corpus; the record keeps its top.
            call["ranking"] = call["ranking"][:TOP]
    return data


def main() -> None:
    """Run the loop on each item of the split and record what it handed over."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model")
    parser.add_argument("--split", choices=SPLITS, default=SPLITS[0])
    parser.add_argument("--records", type=Path)
    args = parser.parse_args()
    model: str = args.model
    split: str = args.split
    written: Path | None = args.records
    items: list[dict[str, Any]] = json.loads(GOLD.read_text(encoding="utf-8"))
    chosen = [item for item in items if item["split"] == split]
    if written is not None:
        lines = written.read_text(encoding="utf-8").splitlines()
        loaded = [json.loads(line) for line in lines]
        ids = [item["id"] for item in chosen]
        try:
            loop_handed(loaded, split, model, ids)
        except ValueError as error:
            parser.error(str(error))
        # In the split's order, which the report zips against.
        by_id = {record["id"]: record for record in loaded}
        print(written)
        summarize([by_id[item_id] for item_id in ids], chosen)
        return
    entries = load_corpus(DATA)
    by_path = {entry.path: entry for entry in entries}
    paths = [entry.path for entry in entries]
    embed = partial(ollama_embed, model=EMBEDDER.model)
    matrix = embed_documents([entry.text for entry in entries], EMBEDDER, embed)
    index = name_index(entries, KINDS)
    dispatch = build_dispatch(EMBEDDER, embed, matrix, paths, index)
    hosted = model.startswith(MODEL_PREFIX)
    source = commit(ROOT)
    config: dict[str, Any] = {
        "model": model,
        "split": split,
        "embedder": EMBEDDER.model,
        "k": K,
        "cap": CALL_CAP,
        "search_k": SEARCH_K,
        "lookup": list(KINDS),
        "commit": source["commit"],
        "dirty": source["dirty"],
    }
    if hosted:
        # Opus 5.5 takes no seed or temperature and cannot turn thinking off.
        config.update({"effort": EFFORT, "max_tokens": MAX_TOKENS})
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
    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"agentic-{stamp}-{split}-{model.replace(':', '-')}.jsonl"
    records: list[dict[str, Any]] = []

    with out.open("w", encoding="utf-8") as file:
        for item in chosen:
            question = item["question"]
            vector = embed_query(question, EMBEDDER, embed)
            question_ranking = rank(vector, matrix, paths)
            backend: Backend = (
                ClaudeBackend(question, model)
                if hosted
                else OllamaBackend(question, model)
            )
            # The whole item is timed, its searches with its turns.
            start = time.perf_counter()
            trace = run_loop(backend, dispatch, by_path)
            seconds = time.perf_counter() - start

            record = {
                "id": item["id"],
                "stopped": trace.stopped,
                "handed": hand_over(trace, question_ranking, K),
                "question": question_ranking[:TOP],
                "links": links(question, index),
                "seconds": round(seconds, 2),
                "trace": trace_record(trace),
                "config": config,
            }
            file.write(json.dumps(record) + "\n")
            records.append(record)
            calls = sum(len(turn.calls) for turn in trace.turns)
            print(f"{item['id']}: {trace.stopped}, {calls} calls in {seconds:.1f}s")

    print(out)
    summarize(records, chosen)


def summarize(records: list[dict[str, Any]], chosen: list[dict[str, Any]]) -> None:
    """Print the loop's retrieval, its lookup tool, the colon items and its cost."""
    report("loop", [r["handed"] for r in records], chosen, KS)
    report("level 1", [r["question"] for r in records], chosen, KS)
    matcher = [lookup_order(r["links"], r["question"], K) for r in records]
    report("matcher", matcher, chosen, KS)

    returned = [
        {
            path
            for call in calls_of(r)
            if call["name"] == "lookup"
            for path in call["ranking"]
        }
        for r in records
    ]
    matched = [set(r["links"]) for r in records]
    hits = sum(
        len(tool & links_) for tool, links_ in zip(returned, matched, strict=True)
    )
    tool_total = sum(len(tool) for tool in returned)
    matcher_total = sum(len(links_) for links_ in matched)
    print(f"lookup tool precision: {ratio(hits, tool_total)} of {tool_total}")
    print(f"lookup tool recall: {ratio(hits, matcher_total)} of {matcher_total}")

    print("colon item              loop   matcher")
    for r, ordered, item in zip(records, matcher, chosen, strict=True):
        if item["id"] in COLON_ITEMS:
            loop_done = all_cites_at_k([(p,) for p in r["handed"]], item["cites"], K)
            matcher_done = all_cites_at_k([(p,) for p in ordered], item["cites"], K)
            print(f"{item['id']:<24}{loop_done!s:<7}{matcher_done!s}")

    count = len(records)
    item_calls = [calls_of(r) for r in records]
    turns = [r["trace"]["turns"] for r in records]
    print("per item, mean")
    print(f"  calls          {sum(len(c) for c in item_calls) / count:.2f}")
    print(f"  turns          {sum(len(t) for t in turns) / count:.2f}")
    input_tokens = sum(turn["input_tokens"] for t in turns for turn in t)
    output_tokens = sum(turn["output_tokens"] for t in turns for turn in t)
    print(f"  input tokens   {input_tokens / count:.0f}")
    print(f"  output tokens  {output_tokens / count:.0f}")
    print(f"  seconds        {sum(r['seconds'] for r in records) / count:.1f}")
    done = sum(r["stopped"] == "done" for r in records)
    capped = sum(r["stopped"] == "cap" for r in records)
    print(f"stopped: done {done}, cap {capped}")
    flat = [call for c in item_calls for call in c]
    invalid = sum(not call["valid"] for call in flat)
    unresolved = sum(
        call["name"] == "lookup" and call["valid"] and not call["ranking"]
        for call in flat
    )
    print(f"invalid calls: {invalid}")
    print(f"lookups told {NO_RECORD!r}: {unresolved}")

    # Input tokens that fall between turns mean a cached prefix went uncounted.
    # strict=False: each turn pairs with the next, so the lists differ by one.
    fell = sum(
        any(
            b["input_tokens"] < a["input_tokens"]
            for a, b in zip(t, t[1:], strict=False)
        )
        for t in turns
    )
    print(f"items whose input tokens fell between turns: {fell} / {count}")


if __name__ == "__main__":
    main()
