"""The endpoint: one question in, its run streamed out as server-sent events.

    python -m uvicorn rules_attorney.server:app

Serves on port 8000 once the corpus is embedded, against the live Ollama
server.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from typing import Any

import ollama
from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel

from rules_attorney.answer import Ruling, chat_request
from rules_attorney.corpus import load_corpus
from rules_attorney.gate import Gate
from rules_attorney.multihop import Plan
from rules_attorney.retrieve import NOMIC, embed_documents, ollama_embed
from rules_attorney.stream import Call, Calls, run

DATA = Path(__file__).resolve().parents[2] / "data" / "srd-5.1"
# The model level 3 was measured on, for the gate, the plan and the ruling.
MODEL = "qwen3.5:9b"

# Async, so a stop or the run's limit cancels the request in flight, which
# closes it and ends Ollama's generation with it.
client = ollama.AsyncClient()


def served(schema: dict[str, Any]) -> Call:
    """A model call through Ollama, held to the schema given."""

    async def call(prompt: str) -> str:
        try:
            response = await client.chat(**chat_request(prompt, MODEL, schema))
        except ollama.ResponseError as error:
            # Ollama is up but refused the call, a model not pulled among the
            # reasons, so the run ends as one whose model cannot be reached.
            raise ConnectionError(str(error)) from error
        return response.message.content or ""

    return call


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Embed the corpus once, at startup, and keep the calls a run makes."""
    entries = load_corpus(DATA)
    embed = partial(ollama_embed, model=NOMIC.model)
    app.state.entries = entries
    app.state.matrix = embed_documents([entry.text for entry in entries], NOMIC, embed)
    app.state.calls = Calls(
        gate=served(Gate.model_json_schema()),
        plan=served(Plan.model_json_schema()),
        answer=served(Ruling.model_json_schema()),
        embed=embed,
    )
    yield


app = FastAPI(lifespan=lifespan)


class Ask(BaseModel):
    """The request body: the question to rule on."""

    question: str


@app.post("/ask", response_class=EventSourceResponse)
async def ask(body: Ask) -> AsyncIterator[ServerSentEvent]:
    """The question's run, one event per stage."""
    state = app.state
    async for event in run(body.question, state.calls, state.entries, state.matrix):
        yield ServerSentEvent(event=event.name, data=event.data)
