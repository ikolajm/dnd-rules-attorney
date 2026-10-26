"""Cut corpus entries into the chunks retrieval ranks, each with the paths it covers."""

from dataclasses import dataclass

from rules_attorney.corpus import Entry


@dataclass(frozen=True)
class Chunk:
    text: str
    paths: tuple[str, ...]


def header_chunks(entries: list[Entry]) -> list[Chunk]:
    """One chunk per entry, its text unchanged and its path its only path."""
    return [Chunk(text=entry.text, paths=(entry.path,)) for entry in entries]


def prepended_chunks(entries: list[Entry]) -> list[Chunk]:
    """One chunk per entry, its ancestors' path above its text, a root unchanged."""
    chunks: list[Chunk] = []

    for entry in entries:
        steps = entry.path.split(" > ")
        ancestors = " > ".join(steps[:-1])
        text = f"{ancestors}\n\n{entry.text}" if ancestors else entry.text
        chunks.append(Chunk(text=text, paths=(entry.path,)))

    return chunks
