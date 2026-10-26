"""Tests for cutting corpus entries into chunks."""

from pathlib import Path

from rules_attorney.chunk import Chunk, header_chunks, prepended_chunks
from rules_attorney.corpus import Entry, load_corpus

DATA = Path(__file__).resolve().parent.parent / "data" / "srd-5.1"
ENTRIES = load_corpus(DATA)


def by_path(chunks: list[Chunk], path: str) -> Chunk:
    """The one chunk whose only path is the one given."""
    return next(chunk for chunk in chunks if chunk.paths == (path,))


def entry_text(path: str) -> str:
    """The corpus text of the entry at the path."""
    entry: Entry = next(entry for entry in ENTRIES if entry.path == path)
    return entry.text


def test_header_chunks_are_one_per_entry_unchanged() -> None:
    chunks = header_chunks(ENTRIES)
    assert [chunk.paths for chunk in chunks] == [(entry.path,) for entry in ENTRIES]
    assert [chunk.text for chunk in chunks] == [entry.text for entry in ENTRIES]


def test_prepended_chunk_opens_with_its_ancestors() -> None:
    path = "making-an-attack > melee-attacks > grappling"
    chunk = by_path(prepended_chunks(ENTRIES), path)
    assert chunk.text == "making-an-attack > melee-attacks\n\n" + entry_text(path)


def test_prepended_chunk_leaves_a_root_unchanged() -> None:
    # cover has no headers under its root, so it has no ancestors.
    chunk = by_path(prepended_chunks(ENTRIES), "cover")
    assert chunk.text == entry_text("cover")


def test_prepended_chunk_never_carries_its_own_path() -> None:
    # The entry's own name already opens its text; the path above it is
    # its ancestors only, so the chunker measures hierarchy, not names.
    for chunk in prepended_chunks(ENTRIES):
        assert not chunk.text.startswith(chunk.paths[0])
