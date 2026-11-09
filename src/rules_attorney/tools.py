"""The tools the loop's model calls, search and lookup."""

from collections.abc import Mapping
from typing import Any

import numpy as np
from anthropic.types import ToolParam
from numpy.typing import NDArray
from pydantic import BaseModel, ValidationError

from rules_attorney.corpus import Entry, render_markdown
from rules_attorney.retrieve import Embed, Embedder, embed_query, rank

# Five, not the ten a ruling is handed, so that several searches' results fit
# in the answering model's context together.
SEARCH_K = 5
NO_RECORD = "No record has that name."
# What each tool does, sent word for word to both backends, so the local rows
# and the hosted one choose between the same two sentences.
SEARCH_DESCRIPTION = (
    "Search the rules for the entries that best match a query, "
    "and return the five best, each under its path. "
    "Name the rule you are looking for the way a rulebook's index would."
)
LOOKUP_DESCRIPTION = (
    "Fetch a record by its exact name: "
    "a spell, condition, weapon property, piece of equipment, "
    "feat, class, race, class feature, racial trait or magic item. "
    "Returns its entry, or says that no record has that name."
)


class SearchArgs(BaseModel):
    """The arguments a search call takes."""

    query: str


class LookupArgs(BaseModel):
    """The arguments a lookup call takes."""

    name: str


TOOLS: tuple[tuple[str, str, type[BaseModel]], ...] = (
    ("search", SEARCH_DESCRIPTION, SearchArgs),
    ("lookup", LOOKUP_DESCRIPTION, LookupArgs),
)
ARGS: dict[str, type[BaseModel]] = {name: args for name, _description, args in TOOLS}


def search(
    query: str,
    *,
    embedder: Embedder,
    embed: Embed,
    matrix: NDArray[np.float64],
    paths: list[str],
    k: int = SEARCH_K,
) -> list[str]:
    """The first k paths retrieval ranks for the query."""
    vector = embed_query(query, embedder, embed)
    ranking = rank(vector, matrix, paths)
    return ranking[:k]


def lookup(name: str, index: dict[str, list[str]]) -> list[str]:
    """The paths of the records the name names, a plural allowed, or none."""
    key = name.strip().lower()
    if key in index:
        return list(index[key])
    if key.endswith("s") and key[:-1] in index:
        return list(index[key[:-1]])
    return []


def render_result(paths: list[str], by_path: dict[str, Entry]) -> str:
    """The entries as markdown under their paths, or NO_RECORD for none."""
    if not paths:
        return NO_RECORD
    return render_markdown([by_path[path] for path in paths])


def ollama_tools() -> list[dict[str, Any]]:
    """The tools as Ollama's chat call declares them."""
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": args.model_json_schema(),
            },
        }
        for name, description, args in TOOLS
    ]


def claude_tools() -> list[ToolParam]:
    """The tools as the Claude API's messages call declares them."""
    return [
        {
            "name": name,
            "description": description,
            "input_schema": args.model_json_schema(),
        }
        for name, description, args in TOOLS
    ]


def valid_call(name: str, arguments: Mapping[str, object]) -> bool:
    """Whether the call names a declared tool and its arguments validate."""
    model = ARGS.get(name)
    if model is None:
        return False
    try:
        model.model_validate(arguments)
    except ValidationError:
        return False
    return True
