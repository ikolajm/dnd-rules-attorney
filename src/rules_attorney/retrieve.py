"""Ranks corpus entries against a question."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
import ollama
from numpy.typing import NDArray


@dataclass(frozen=True)
class Embedder:
    """An embedding model and the prefixes its card asks for."""

    model: str
    query_prefix: str
    document_prefix: str


NOMIC = Embedder(
    model="nomic-embed-text",
    query_prefix="search_query: ",
    document_prefix="search_document: ",
)
GEMMA = Embedder(
    model="embeddinggemma-2:270m",
    query_prefix="task: search result | query: ",
    document_prefix="title: none | text: ",
)
QWEN_TASK = (
    "Given a question about D&D 5e rules, retrieve the rules sections that answer it"
)
QWEN = Embedder(
    model="qwen3-embedding:0.6b",
    query_prefix=f"Instruct: {QWEN_TASK}\nQuery:",
    document_prefix="",
)
EMBEDDERS = (NOMIC, GEMMA, QWEN)

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


def embed_documents(
    texts: list[str], embedder: Embedder, embed: Embed
) -> NDArray[np.float64]:
    """The entries' vectors, each text sent with the embedder's document prefix."""
    return embed([embedder.document_prefix + text for text in texts])


def embed_query(question: str, embedder: Embedder, embed: Embed) -> NDArray[np.float64]:
    """The question's vector, sent with the embedder's query prefix."""
    vectors = embed([embedder.query_prefix + question])
    vector: NDArray[np.float64] = vectors[0]
    return vector


def ollama_embed(texts: list[str], *, model: str) -> NDArray[np.float64]:
    """Embed through Ollama with the model named, in batches, refusing truncation."""
    vectors: list[Sequence[float]] = []
    for start in range(0, len(texts), EMBED_BATCH):
        batch = texts[start : start + EMBED_BATCH]
        response = ollama.embed(model=model, input=batch, truncate=False)
        vectors.extend(response.embeddings)
    return np.array(vectors, dtype=np.float64)
