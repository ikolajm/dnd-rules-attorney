"""Cut corpus entries into the chunks retrieval ranks, each with the paths it covers."""

from dataclasses import dataclass
from itertools import groupby

from rules_attorney.corpus import Entry

# Sources hold one record per entry
WHOLE = ("conditions", "spells", "weapon-properties")
WINDOW = 800
OVERLAP = 200
SEPARATOR = "\n\n"


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


def record_key(path: str) -> str:
    """The source record a path belongs to: its rule section, or itself."""
    steps = path.split(" > ")
    if steps[0] in WHOLE:
        return " > ".join(steps[:2])
    return steps[0]


def records(entries: list[Entry]) -> list[list[Entry]]:
    """Neighbouring entries of one source record grouped, in corpus order."""
    return [
        list(group)
        for _, group in groupby(entries, key=lambda entry: record_key(entry.path))
    ]


def windows(length: int, size: int, overlap: int) -> list[tuple[int, int]]:
    """Half-open spans of size, each starting size - overlap after the last."""
    spans = []
    for start in range(0, length, size - overlap):
        end = min(start + size, length)
        spans.append((start, end))

        if end == length:
            break

    return spans


def overlapping(
    spans: list[tuple[int, int, str]], start: int, end: int
) -> tuple[str, ...]:
    """The paths of the spans sharing a character with the window, in order."""
    return tuple(
        path
        for span_start, span_end, path in spans
        if span_start < end and start < span_end
    )


def joined(record: list[Entry]) -> tuple[str, list[tuple[int, int, str]]]:
    """The record's texts joined by SEPARATOR, and each entry's span and path in it."""
    spans: list[tuple[int, int, str]] = []
    position = 0

    for entry in record:
        spans.append((position, position + len(entry.text), entry.path))
        position += len(entry.text) + len(SEPARATOR)

    text = SEPARATOR.join(entry.text for entry in record)
    return text, spans


def window_chunks(entries: list[Entry]) -> list[Chunk]:
    """Fixed windows over each record's joined text, each with the paths it overlaps."""
    chunks: list[Chunk] = []
    for record in records(entries):
        text, spans = joined(record)

        for start, end in windows(len(text), WINDOW, OVERLAP):
            chunks.append(
                Chunk(text=text[start:end], paths=overlapping(spans, start, end))
            )

    return chunks
