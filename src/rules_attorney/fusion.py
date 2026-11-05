"""Fuses several rankings of the same labels into one."""

# Reciprocal rank fusion's usual constant, untuned.
CONSTANT = 60

# A whole ranking scores every entry, so one middling everywhere outscores
# one first in a few. Ten is the shallowest depth that hands over ten on every
# dev item.
FUSE_DEPTH = 10


def fused_scores(
    rankings: list[list[str]], constant: int = CONSTANT
) -> dict[str, float]:
    """Each label's 1 / (constant + rank) summed over the rankings, rank from 1."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for position, label in enumerate(ranking, start=1):
            scores[label] = scores.get(label, 0.0) + 1 / (constant + position)

    return scores


def fuse(rankings: list[list[str]], constant: int = CONSTANT) -> list[str]:
    """The labels best first by their fused scores."""
    scores = fused_scores(rankings, constant)
    return sorted(scores, key=lambda label: scores[label], reverse=True)


def fuse_tops(rankings: list[list[str]], depth: int = FUSE_DEPTH) -> list[str]:
    """The labels best first, each ranking cut to depth before fusing."""
    return fuse([ranking[:depth] for ranking in rankings])
