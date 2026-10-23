"""Tests for embedding and ranking corpus entries against a question."""

from typing import Any

import numpy as np
import ollama
import pytest
from numpy.typing import NDArray

from rules_attorney.retrieve import embed_documents, embed_query, ollama_embed, rank


def test_rank_orders_by_cosine() -> None:
    question = np.array([1.0, 0.0])
    entries = np.array([[0.0, 1.0], [1.0, 0.0], [1.0, 1.0]])
    assert rank(question, entries, ["far", "near", "mid"]) == ["near", "mid", "far"]


def test_rank_ignores_length() -> None:
    question = np.array([1.0, 0.0])
    entries = np.array([[1.0, 0.1], [2.0, 20.0]])
    assert rank(question, entries, ["near", "long-far"]) == ["near", "long-far"]


def test_embed_documents_adds_the_document_prefix() -> None:
    sent: list[list[str]] = []

    def fake(texts: list[str]) -> NDArray[np.float64]:
        sent.append(texts)
        return np.zeros((len(texts), 2))

    embed_documents(["first entry", "second entry"], fake)
    assert sent == [["search_document: first entry", "search_document: second entry"]]


def test_embed_query_adds_the_query_prefix() -> None:
    sent: list[list[str]] = []

    def fake(texts: list[str]) -> NDArray[np.float64]:
        sent.append(texts)
        return np.zeros((len(texts), 2))

    vector = embed_query("can I drag a grappled creature", fake)
    assert sent == [["search_query: can I drag a grappled creature"]]
    assert vector.shape == (2,)


def test_ollama_embed_refuses_truncation(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake(**kwargs: Any) -> ollama.EmbedResponse:
        calls.append(kwargs)
        return ollama.EmbedResponse(embeddings=[[0.0, 1.0]])

    monkeypatch.setattr(ollama, "embed", fake)
    ollama_embed(["an entry"])
    assert calls[0].get("truncate") is False
