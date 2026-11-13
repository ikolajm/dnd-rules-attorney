"""Link the records each question names ahead of level 1, and score both orders.

    python scripts/evals/eval_lookup.py [--split dev|test] [--kinds <root> ...]

Embeds through the live Ollama server. The split is dev unless test is named,
and --kinds names the path roots a name links from, every root in KINDS unless
given.
"""

import argparse
import json
from collections import Counter
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

from rules_attorney.corpus import load_corpus
from rules_attorney.evals.metrics import report
from rules_attorney.evals.provenance import commit
from rules_attorney.evals.split import SPLITS
from rules_attorney.lookup import KINDS, links, lookup_order, name_index
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


def link_line(name: str, linked: int, cited: int, cites: int) -> str:
    """One kind's links, cited links, precision, cites and recall, as a row."""
    precision = f"{cited / linked:.3f}" if linked else "-"
    recall = f"{cited / cites:.3f}" if cites else "-"
    return f"{name:<18}{linked:>6}{cited:>6}{precision:>10}{cites:>6}{recall:>8}"


def main() -> None:
    """Link and rank each item of the split, and score both orders."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--split", choices=SPLITS, default=SPLITS[0])
    parser.add_argument("--kinds", choices=KINDS, nargs="+", default=list(KINDS))
    args = parser.parse_args()
    split: str = args.split
    kinds: list[str] = args.kinds
    entries = load_corpus(DATA)
    paths = [entry.path for entry in entries]
    items: list[dict[str, Any]] = json.loads(GOLD.read_text(encoding="utf-8"))
    chosen = [item for item in items if item["split"] == split]
    embed = partial(ollama_embed, model=EMBEDDER.model)
    matrix = embed_documents([entry.text for entry in entries], EMBEDDER, embed)
    index = name_index(entries, tuple(kinds))
    source = commit(ROOT)
    config: dict[str, Any] = {
        "split": split,
        "embedder": EMBEDDER.model,
        "kinds": kinds,
        "commit": source["commit"],
        "dirty": source["dirty"],
    }
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"lookup-{stamp}-{split}.jsonl"
    befores: list[list[str]] = []
    orders: list[list[str]] = []
    link_counts: Counter[str] = Counter()
    cited_link_counts: Counter[str] = Counter()
    cite_counts: Counter[str] = Counter()
    with out.open("w", encoding="utf-8") as file:
        for item in chosen:
            vector = embed_query(item["question"], EMBEDDER, embed)
            before = rank(vector, matrix, paths)[: KS[-1]]
            linked = links(item["question"], index)
            order = lookup_order(linked, before, KS[-1])
            befores.append(before)
            orders.append(order)
            cited = set(item["cites"])
            for path in linked:
                root = path.split(" > ")[0]
                link_counts[root] += 1
                if path in cited:
                    cited_link_counts[root] += 1
            for cite in item["cites"]:
                root = cite.split(" > ")[0]
                if root in kinds:
                    cite_counts[root] += 1
            record: dict[str, Any] = {
                "id": item["id"],
                "linked": linked,
                "before": before,
                "order": order,
                "config": config,
            }
            file.write(json.dumps(record) + "\n")

    print(out)
    report("level 1", befores, chosen, KS)
    report("level 1 + lookup", orders, chosen, KS)
    print(
        f"{'kind':<18}{'links':>6}{'cited':>6}{'precision':>10}{'cites':>6}{'recall':>8}"
    )
    for root in kinds:
        print(
            link_line(
                root, link_counts[root], cited_link_counts[root], cite_counts[root]
            )
        )
    print(
        link_line(
            "all",
            link_counts.total(),
            cited_link_counts.total(),
            cite_counts.total(),
        )
    )


if __name__ == "__main__":
    main()
