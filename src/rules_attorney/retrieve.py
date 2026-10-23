"""Ranks corpus entries against a question."""

from collections.abc import Callable

import numpy as np
import ollama
from numpy.typing import NDArray

MODEL = "nomic-embed-text"
QUERY_PREFIX = "search_query: "
DOCUMENT_PREFIX = "search_document: "


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
    """Embed through Ollama, refusing any input past the model's context."""
    response = ollama.embed(model=MODEL, input=texts, truncate=False)
    return np.array(response.embeddings, dtype=np.float64)
