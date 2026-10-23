"""BM25 keyword retrieval in its Lucene form."""

import math
import re
from collections import Counter
from dataclasses import dataclass

TOKEN = re.compile(r"[a-z0-9]+")
K1 = 1.2
B = 0.75


def tokenize(text: str) -> list[str]:
    """The text's words, lowercased, split on anything not a letter or digit."""
    return TOKEN.findall(text.lower())


def idf(containing: int, total: int) -> float:
    """Lucene's inverse document frequency for a word in containing of total entries."""
    return math.log(1 + (total - containing + 0.5) / (containing + 0.5))


def term_score(count: int, length: int, average: float, weight: float) -> float:
    """One word's BM25 contribution to one entry."""
    norm = K1 * (1 - B + B * length / average)
    return weight * count / (count + norm)


@dataclass(frozen=True)
class Index:
    """The counted corpus BM25 scores against, built once."""

    paths: list[str]
    counts: list[Counter[str]]
    lengths: list[int]
    average: float
    weights: dict[str, float]


def build_index(paths: list[str], texts: list[str]) -> Index:
    """Count every entry's words and weigh each word by IDF."""
    counts = [Counter(tokenize(text)) for text in texts]
    lengths = [counter.total() for counter in counts]
    containing: Counter[str] = Counter()

    for counter in counts:
        containing.update(counter.keys())

    weights = {word: idf(n, len(texts)) for word, n in containing.items()}

    return Index(
        paths=paths,
        counts=counts,
        lengths=lengths,
        average=(sum(lengths) / len(lengths)),
        weights=weights,
    )


def scores(index: Index, question: str) -> list[float]:
    """Every entry's BM25 score for the question, in corpus order."""
    words = tokenize(question)
    result: list[float] = []

    for counter, length in zip(index.counts, index.lengths, strict=True):
        total = 0.0
        for word in words:
            if word in counter:
                total += term_score(
                    counter[word], length, index.average, index.weights[word]
                )
        result.append(total)

    return result


def bm25_rank(index: Index, question: str) -> list[str]:
    """Paths best first by BM25 score."""
    entry_scores = scores(index, question)
    order = sorted(
        range(len(entry_scores)), key=lambda i: entry_scores[i], reverse=True
    )
    return [index.paths[i] for i in order]
