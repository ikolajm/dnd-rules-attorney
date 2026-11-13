"""Scores retrieval against gold cites."""

from typing import Any


def recall_at_k(ranked: list[tuple[str, ...]], cites: list[str], k: int) -> float:
    """The share of the item's cites found in the paths of the first k ranked chunks."""
    top = {path for chunk in ranked[:k] for path in chunk}
    found = sum(1 for cite in cites if cite in top)
    return found / len(cites)


def all_cites_at_k(ranked: list[tuple[str, ...]], cites: list[str], k: int) -> bool:
    """Whether all the item's cites are in the paths of the first k ranked chunks."""
    top = {path for chunk in ranked[:k] for path in chunk}
    return all(cite in top for cite in cites)


def report(
    name: str, rankings: list[list[str]], chosen: list[dict[str, Any]], ks: list[int]
) -> None:
    """Print recall@k and all-cites@k at each k for one order of entry paths."""
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
