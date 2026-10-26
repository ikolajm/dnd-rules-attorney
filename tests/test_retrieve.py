"""Tests for embedding and ranking corpus entries against a question."""

from typing import Any

import numpy as np
import ollama
import pytest
from numpy.typing import NDArray

from rules_attorney.retrieve import (
    EMBED_BATCH,
    NOMIC,
    QWEN,
    QWEN_TASK,
    Embed,
    Embedder,
    embed_documents,
    embed_query,
    ollama_embed,
    rank,
)

# Two different prefixes, so a function reading the wrong one fails.
STAND_IN = Embedder(model="stand-in", query_prefix="ask: ", document_prefix="doc: ")


def recording(sent: list[list[str]]) -> Embed:
    """A fake embed that keeps every batch of texts it is sent."""

    def fake(texts: list[str]) -> NDArray[np.float64]:
        sent.append(texts)
        return np.zeros((len(texts), 2))

    return fake


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
    embed_documents(["first entry", "second entry"], STAND_IN, recording(sent))
    assert sent == [["doc: first entry", "doc: second entry"]]


def test_embed_query_adds_the_query_prefix() -> None:
    sent: list[list[str]] = []
    vector = embed_query("can I drag a grappled creature", STAND_IN, recording(sent))
    assert sent == [["ask: can I drag a grappled creature"]]
    assert vector.shape == (2,)


def test_an_empty_document_prefix_leaves_the_text_unchanged() -> None:
    sent: list[list[str]] = []
    embed_documents(["first entry"], QWEN, recording(sent))
    assert sent == [["first entry"]]


def test_the_qwen_query_is_its_instruction_then_query_with_no_space() -> None:
    # The card's form: a real newline, and the question straight after
    # `Query:`. A raw string or an added space would still run, worse.
    sent: list[list[str]] = []
    embed_query("can I drag a grappled creature", QWEN, recording(sent))
    expected = f"Instruct: {QWEN_TASK}\nQuery:can I drag a grappled creature"
    assert sent == [[expected]]


def test_nomic_keeps_the_settings_earlier_runs_used() -> None:
    # Every run before the embedder comparison recorded these, so a change
    # here would make the same model read as a different one.
    before = Embedder(
        model="nomic-embed-text",
        query_prefix="search_query: ",
        document_prefix="search_document: ",
    )
    assert before == NOMIC


def test_ollama_embed_sends_the_model_named(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake(**kwargs: Any) -> ollama.EmbedResponse:
        calls.append(kwargs)
        return ollama.EmbedResponse(embeddings=[[0.0, 1.0]])

    monkeypatch.setattr(ollama, "embed", fake)
    ollama_embed(["an entry"], model="stand-in")
    assert calls[0]["model"] == "stand-in"


def test_ollama_embed_refuses_truncation(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake(**kwargs: Any) -> ollama.EmbedResponse:
        calls.append(kwargs)
        return ollama.EmbedResponse(embeddings=[[0.0, 1.0]])

    monkeypatch.setattr(ollama, "embed", fake)
    ollama_embed(["an entry"], model="stand-in")
    assert calls[0].get("truncate") is False


def test_ollama_embed_batches_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake(**kwargs: Any) -> ollama.EmbedResponse:
        calls.append(kwargs)
        return ollama.EmbedResponse(embeddings=[[float(t)] for t in kwargs["input"]])

    monkeypatch.setattr(ollama, "embed", fake)
    count = 2 * EMBED_BATCH + 20
    vectors = ollama_embed([str(i) for i in range(count)], model="stand-in")
    assert [len(call["input"]) for call in calls] == [EMBED_BATCH, EMBED_BATCH, 20]
    assert all(call.get("truncate") is False for call in calls)
    assert vectors[:, 0].tolist() == [float(i) for i in range(count)]
