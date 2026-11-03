"""Reorders retrieval's top entries by a cross-encoder's scores."""

from collections.abc import Callable

from rules_attorney.corpus import Entry

type Score = Callable[[list[tuple[str, str]]], list[float]]

# The entries reordered, of which ten are handed over. The dev records stop
# at 20, so 30 reaches past what level 1 has been measured at.
DEPTH = 30

# Its window holds the longest entry; the scorer refuses any pair past it.
RERANKER = "BAAI/bge-reranker-v2-m3"


def rerank(question: str, entries: list[Entry], score: Score) -> list[str]:
    """The entries' paths, best score first; a tie keeps the order given."""
    pairs = [(question, entry.text) for entry in entries]
    scores = score(pairs)
    ranked = sorted(
        zip(entries, scores, strict=True), key=lambda pair: pair[1], reverse=True
    )
    return [entry.path for entry, _ in ranked]
