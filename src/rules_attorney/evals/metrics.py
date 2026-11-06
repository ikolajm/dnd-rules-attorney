"""Scores retrieval against gold cites."""


def recall_at_k(ranked: list[tuple[str, ...]], cites: list[str], k: int) -> float:
    """The share of the item's cites found in the paths of the first k ranked chunks."""
    top = {path for chunk in ranked[:k] for path in chunk}
    found = sum(1 for cite in cites if cite in top)
    return found / len(cites)


def all_cites_at_k(ranked: list[tuple[str, ...]], cites: list[str], k: int) -> bool:
    """Whether all the item's cites are in the paths of the first k ranked chunks."""
    top = {path for chunk in ranked[:k] for path in chunk}
    return all(cite in top for cite in cites)
