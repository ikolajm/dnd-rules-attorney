"""Ranks corpus entries against a question."""

import numpy as np
from numpy.typing import NDArray


def rank(
    question: NDArray[np.float64], entries: NDArray[np.float64], paths: list[str]
) -> list[str]:
    """Paths ordered best match first, by cosine similarity."""
    q = question / np.linalg.norm(question)
    unit = entries / np.linalg.norm(entries, axis=1, keepdims=True)
    scores = unit @ q
    order = np.argsort(scores)[::-1]

    return [paths[i] for i in order]
