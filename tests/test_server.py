"""Tests for the endpoint's model calls."""

import asyncio
from typing import Any

import ollama
import pytest

from rules_attorney import server
from rules_attorney.gate import Gate


def test_a_model_ollama_refuses_counts_as_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def refuse(**request: Any) -> None:
        # What Ollama answers for a model that has not been pulled.
        raise ollama.ResponseError("model 'qwen3.5:9b' not found", 404)

    monkeypatch.setattr(server.client, "chat", refuse)
    call = server.served(Gate.model_json_schema())
    with pytest.raises(ConnectionError):
        asyncio.run(call("Can a grappled creature attack?"))
