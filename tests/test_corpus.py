"""Tests for building the citable corpus."""

import json
from pathlib import Path

import pytest

from rules_attorney.corpus import (
    SECTIONS_FILE,
    SOURCES,
    CorpusError,
    load_corpus,
    section_entries,
    slug,
)

DATA = Path(__file__).resolve().parent.parent / "data" / "srd-5.1"


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("Verbal (V)", "verbal-v"),
        ("Variant: Encumbrance", "variant-encumbrance"),
        ("What Is a Spell?", "what-is-a-spell"),
        ("Climbing, Swimming, and Crawling", "climbing-swimming-and-crawling"),
        ("Two-Weapon Fighting", "two-weapon-fighting"),
    ],
)
def test_slug(given: str, expected: str) -> None:
    assert slug(given) == expected


def test_section_entries_nests_headers() -> None:
    desc = "\n".join(
        [
            "## Root Header",
            "root text",
            "### Child",
            "child text",
            "#### Grandchild",
            "grandchild text",
            "## Sibling",
            "sibling text",
        ]
    )
    entries = section_entries({"index": "the-root", "desc": desc})
    assert [e.path for e in entries] == [
        "the-root",
        "the-root > child",
        "the-root > child > grandchild",
        "the-root > sibling",
    ]
    assert entries[1].text == "child text"


def test_load_corpus_refuses_duplicate_paths(tmp_path: Path) -> None:
    desc = "\n".join(["## Root", "### Same", "a", "### Same", "b"])
    sections = [{"index": "the-root", "desc": desc}]
    for name in SOURCES:
        (tmp_path / name).write_text(json.dumps([]), encoding="utf-8")
    (tmp_path / SECTIONS_FILE).write_text(json.dumps(sections), encoding="utf-8")
    with pytest.raises(CorpusError, match="the-root > same"):
        load_corpus(tmp_path)


@pytest.mark.parametrize(
    "path",
    [
        "making-an-attack > melee-attacks > grappling",
        "the-planes-of-existence > the-material-plane",
        "movement > speed > travel-pace > travel-pace",
        "conditions > grappled",
        "weapon-properties > two-handed",
        "weapon-properties > monk",
    ],
)
def test_committed_corpus_holds_known_paths(path: str) -> None:
    paths = {e.path for e in load_corpus(DATA)}
    assert path in paths
