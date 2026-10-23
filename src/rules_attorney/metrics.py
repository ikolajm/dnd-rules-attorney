"""Scores retrieval against gold cites."""


def recall_at_k(ranked: list[str], cites: list[str], k: int) -> float:
    """The share of the item's cites found in the first k ranked paths."""
    top = set(ranked[:k])
    found = sum(1 for cite in cites if cite in top)
    return found / len(cites)


def all_cites_at_k(ranked: list[str], cites: list[str], k: int) -> bool:
    """Whether every one of the item's cites is in the first k ranked paths."""
    top = set(ranked[:k])
    return all(cite in top for cite in cites)
