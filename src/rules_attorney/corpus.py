"""Build the citable corpus from the SRD source files."""

import json
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SECTIONS_FILE = "5e-SRD-Rule-Sections.json"
CONDITIONS_FILE = "5e-SRD-Conditions.json"
WEAPON_PROPERTIES_FILE = "5e-SRD-Weapon-Properties.json"
SPELLS_FILE = "5e-SRD-Spells.json"


def slug(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9 -]", "", text)
    text = re.sub(r"[ -]+", "-", text)
    text = text.strip("-")
    return text


class CorpusError(Exception):
    """A corpus the build refuses."""


@dataclass(frozen=True)
class Entry:
    path: str
    text: str


type Parser = Callable[[dict[str, Any]], list[Entry]]


def section_entries(record: dict[str, Any]) -> list[Entry]:
    """Split one rule section's markdown into an entry per header."""
    index: str = record["index"]
    desc: str = record["desc"]
    stack: list[tuple[int, str]] = []
    found: list[tuple[str, list[str]]] = []
    for line in desc.splitlines():
        m = re.match(r"^(#+)\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            if not stack:
                stack.append((level, index))
            else:
                while len(stack) > 1 and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, slug(m.group(2))))
            path = " > ".join(step for _, step in stack)
            found.append((path, []))
        elif found:
            found[-1][1].append(line)
    return [Entry(path, "\n".join(lines).strip()) for path, lines in found]


def condition_entries(record: dict[str, Any]) -> list[Entry]:
    """Make the single entry for one condition, cited whole."""
    index: str = record["index"]
    desc: list[str] = record["desc"]
    path = f"conditions > {index}"
    text = "\n\n".join(desc)
    return [Entry(path=path, text=text)]


def weapon_property_entries(record: dict[str, Any]) -> list[Entry]:
    """Make the single entry for one weapon property, cited whole."""
    index: str = record["index"]
    desc: list[str] = record["desc"]
    path = f"weapon-properties > {index}"
    text = "\n\n".join(desc)
    return [Entry(path=path, text=text)]


def spell_entries(record: dict[str, Any]) -> list[Entry]:
    """Make the single entry for one spell, its fields as lines above its text."""
    index: str = record["index"]
    desc: list[str] = record["desc"]
    path = f"spells > {index}"

    lines: list[str] = []
    level: int = record["level"]
    lines.append(f"Level: {'cantrip' if level == 0 else level}")
    lines.append(f"School: {record['school']['name']}")
    lines.append(f"Casting time: {record['casting_time']}")
    lines.append(f"Range: {record['range']}")

    components = ", ".join(record["components"])
    material: str | None = record.get("material")
    if material:
        components += f" ({material})"
    lines.append(f"Components: {components}")
    lines.append(f"Duration: {record['duration']}")
    lines.append(f"Concentration: {'yes' if record['concentration'] else 'no'}")
    lines.append(f"Ritual: {'yes' if record['ritual'] else 'no'}")

    blocks: list[str] = ["\n".join(lines), "\n\n".join(desc)]
    higher: list[str] | None = record.get("higher_level")
    if higher:
        blocks.append("At Higher Levels. " + "\n\n".join(higher))
    text = "\n\n".join(blocks)
    return [Entry(path=path, text=text)]


SOURCES: dict[str, Parser] = {
    SECTIONS_FILE: section_entries,
    CONDITIONS_FILE: condition_entries,
    WEAPON_PROPERTIES_FILE: weapon_property_entries,
    SPELLS_FILE: spell_entries,
}


def load_corpus(data_dir: Path) -> list[Entry]:
    """Read every source file, refusing duplicate paths."""
    entries: list[Entry] = []
    for name, parse in SOURCES.items():
        text = (data_dir / name).read_text(encoding="utf-8")
        records: list[dict[str, Any]] = json.loads(text)
        for record in records:
            entries.extend(parse(record))

    counts = Counter(e.path for e in entries)
    dupes = sorted(path for path, n in counts.items() if n > 1)
    if dupes:
        raise CorpusError(f"duplicate paths: {', '.join(dupes)}")
    return entries


def render_markdown(entries: list[Entry]) -> str:
    """Render entries as markdown, each path as a level-2 header."""
    blocks: list[str] = []
    for entry in entries:
        block = f"## {entry.path}\n\n{entry.text}"
        blocks.append(block)
    return "\n\n".join(blocks)
