"""Ranks corpus entries against a question."""

from collections.abc import Callable, Sequence

import numpy as np
import ollama
from numpy.typing import NDArray

MODEL = "nomic-embed-text"
QUERY_PREFIX = "search_query: "
DOCUMENT_PREFIX = "search_document: "
# Ollama on Windows refuses a single request of several hundred inputs, its
# runner turning away the connections, so inputs go out in batches.
EMBED_BATCH = 50


type Embed = Callable[[list[str]], NDArray[np.float64]]


def rank(
    question: NDArray[np.float64], entries: NDArray[np.float64], paths: list[str]
) -> list[str]:
    """Paths ordered best match first, by cosine similarity."""
    q = question / np.linalg.norm(question)
    unit = entries / np.linalg.norm(entries, axis=1, keepdims=True)
    scores = unit @ q
    order = np.argsort(scores)[::-1]

    return [paths[i] for i in order]


def embed_documents(texts: list[str], embed: Embed) -> NDArray[np.float64]:
    """The entries' vectors, each text sent with the document prefix."""
    return embed([DOCUMENT_PREFIX + text for text in texts])


def embed_query(question: str, embed: Embed) -> NDArray[np.float64]:
    """The question's vector, sent with the query prefix."""
    vectors = embed([QUERY_PREFIX + question])
    vector: NDArray[np.float64] = vectors[0]
    return vector


def ollama_embed(texts: list[str]) -> NDArray[np.float64]:
    """Embed through Ollama in batches, refusing any input past the context."""
    vectors: list[Sequence[float]] = []
    for start in range(0, len(texts), EMBED_BATCH):
        batch = texts[start : start + EMBED_BATCH]
        response = ollama.embed(model=MODEL, input=batch, truncate=False)
        vectors.extend(response.embeddings)
    return np.array(vectors, dtype=np.float64)
