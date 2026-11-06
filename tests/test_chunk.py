"""Tests for cutting corpus entries into chunks."""

import json
from pathlib import Path
from typing import Any

from rules_attorney.corpus import (
    EQUIPMENT_FILE,
    EQUIPMENT_KINDS,
    FEATURES_FILE,
    FOCI,
    GEAR_WITH_RULES,
    SOURCES,
    SUPPLEMENT_FILE,
    TRAITS_FILE,
    Entry,
    load_corpus,
)
from rules_attorney.evals.chunk import (
    Chunk,
    header_chunks,
    joined,
    overlapping,
    prepended_chunks,
    records,
    window_chunks,
    windows,
)

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


def test_records_match_the_source_files() -> None:
    # Counted from the files, so the test follows the data rather than a
    # number typed in. A rule section is one record of many entries; a
    # condition, spell, weapon property, weapon or armor is one record of
    # one, as is gear with a rule and each spellcasting focus; other gear
    # makes no entry. Class features and racial traits are one record per
    # distinct text, however many repeat it; a race, class or feat is one
    # record of one. The supplement's new entries group by their first step,
    # as a rule section's do; its other passages join entries already counted.
    expected = 0
    for name in SOURCES:
        rows: list[dict[str, Any]] = json.loads(
            (DATA / name).read_text(encoding="utf-8")
        )
        if name == EQUIPMENT_FILE:
            rows = [
                r
                for r in rows
                if r["equipment_category"]["index"] in EQUIPMENT_KINDS
                or r["index"] in GEAR_WITH_RULES
            ]
            expected += len(FOCI)
        if name in (FEATURES_FILE, TRAITS_FILE):
            expected += len({"\n\n".join(r["desc"]) for r in rows})
            continue
        expected += len(rows)
    supplement = json.loads((DATA / SUPPLEMENT_FILE).read_text(encoding="utf-8"))
    steps = [
        p["path"].split(" > ")[0] for p in supplement["passages"] if p["op"] == "new"
    ]
    expected += sum(1 for i, step in enumerate(steps) if i == 0 or step != steps[i - 1])
    assert len(records(ENTRIES)) == expected


def test_windows_cut_a_long_text_with_overlap() -> None:
    assert windows(2000, 800, 200) == [(0, 800), (600, 1400), (1200, 2000)]


def test_windows_leave_a_short_text_whole() -> None:
    assert windows(500, 800, 200) == [(0, 500)]


def test_windows_leave_no_gap_and_reach_the_end() -> None:
    for length in (1, 799, 800, 801, 1400, 1401, 4247):
        spans = windows(length, 800, 200)
        assert spans[0][0] == 0
        assert spans[-1][1] == length
        for (_, previous_end), (next_start, _) in zip(spans, spans[1:], strict=False):
            assert next_start <= previous_end


def test_overlapping_leaves_out_a_span_ending_where_the_window_starts() -> None:
    # Spans are half-open: a span ending at 600 holds no character of a
    # window starting at 600.
    spans = [(0, 600, "a"), (602, 900, "b")]
    assert overlapping(spans, 600, 1400) == ("b",)


def test_overlapping_takes_a_span_crossing_the_window_start() -> None:
    assert overlapping([(0, 700, "a")], 600, 1400) == ("a",)


def test_joined_spans_slice_back_each_entry() -> None:
    # The position count has to step over the separator exactly; a drift
    # of a few characters mislabels windows without losing any path.
    for record in records(ENTRIES):
        text, spans = joined(record)
        for (start, end, path), entry in zip(spans, record, strict=True):
            assert path == entry.path
            assert text[start:end] == entry.text


def test_every_path_is_in_a_window() -> None:
    covered = {path for chunk in window_chunks(ENTRIES) for path in chunk.paths}
    assert covered == {entry.path for entry in ENTRIES}
