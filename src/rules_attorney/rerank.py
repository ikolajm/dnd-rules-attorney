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


class TruncationError(Exception):
    """A pair longer than the reranker's window, which it would cut silently."""


def refuse_truncation(lengths: list[int], limit: int) -> None:
    """Raise when any pair's token count is past the limit."""
    longest = max(lengths, default=0)
    if longest > limit:
        raise TruncationError(
            f"a pair of {longest} tokens is past the {limit}-token window"
        )


def cross_encoder(model: str) -> Score:
    """A Score backed by the cross-encoder named, loaded once."""
    # Imported here, so torch loads only when a real scorer is built and an
    # install without the rerank extra still runs the tests.
    from sentence_transformers import CrossEncoder

    encoder = CrossEncoder(model)

    def score(pairs: list[tuple[str, str]]) -> list[float]:
        lengths = [
            len(encoder.tokenizer(question, text)["input_ids"])
            for question, text in pairs
        ]
        refuse_truncation(lengths, encoder.max_length)
        scores = encoder.predict(pairs)
        return [float(value) for value in scores]

    return score
