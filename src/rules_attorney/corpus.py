"""Build the citable corpus from the SRD source files."""

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SECTIONS_FILE = "5e-SRD-Rule-Sections.json"
CONDITIONS_FILE = "5e-SRD-Conditions.json"


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


def section_entries(index: str, desc: str) -> list[Entry]:
    """Split one rule section's markdown into an entry per header."""
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


def condition_entry(index: str, desc: list[str]) -> Entry:
    """Make the single entry for one condition, cited whole."""
    path = f"conditions > {index}"
    text = "\n\n".join(desc)
    return Entry(path=path, text=text)


def load_corpus(data_dir: Path) -> list[Entry]:
    """Read both source files into entries, refusing duplicate paths."""
    sections_text = (data_dir / SECTIONS_FILE).read_text(encoding="utf-8")
    sections: list[dict[str, Any]] = json.loads(sections_text)
    conditions_text = (data_dir / CONDITIONS_FILE).read_text(encoding="utf-8")
    conditions: list[dict[str, Any]] = json.loads(conditions_text)

    entries: list[Entry] = []
    for s in sections:
        entries.extend(section_entries(s["index"], s["desc"]))
    for c in conditions:
        entries.append(condition_entry(c["index"], c["desc"]))

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
