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
EQUIPMENT_FILE = "5e-SRD-Equipment.json"

# The equipment categories that become entries; the rest of the file is gear,
# a lookup rather than a dispute.
EQUIPMENT_KINDS = ("weapon", "armor")


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
        header = re.match(r"^(?P<hashes>#+)\s+(?P<text>.*)$", line)
        if header:
            level = len(header["hashes"])
            if not stack:
                stack.append((level, index))
            else:
                while len(stack) > 1 and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, slug(header["text"])))
            path = " > ".join(step for _, step in stack)
            found.append((path, [header["text"]]))
        elif found:
            found[-1][1].append(line)
    return [Entry(path, "\n".join(lines).strip()) for path, lines in found]


def condition_entries(record: dict[str, Any]) -> list[Entry]:
    """Make the single entry for one condition, cited whole."""
    index: str = record["index"]
    desc: list[str] = record["desc"]
    name: str = record["name"]
    path = f"conditions > {index}"
    text = "\n\n".join([name, *desc])
    return [Entry(path=path, text=text)]


def weapon_property_entries(record: dict[str, Any]) -> list[Entry]:
    """Make the single entry for one weapon property, cited whole."""
    index: str = record["index"]
    desc: list[str] = record["desc"]
    name: str = record["name"]
    path = f"weapon-properties > {index}"
    text = "\n\n".join([name, *desc])
    return [Entry(path=path, text=text)]


def spell_entries(record: dict[str, Any]) -> list[Entry]:
    """Make the single entry for one spell, the spell's name, then fields, then text."""
    index: str = record["index"]
    name: str = record["name"]
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

    blocks: list[str] = [name, "\n".join(lines), "\n\n".join(desc)]
    higher: list[str] | None = record.get("higher_level")
    if higher:
        blocks.append("At Higher Levels. " + "\n\n".join(higher))
    text = "\n\n".join(blocks)
    return [Entry(path=path, text=text)]


def span(distance: dict[str, int]) -> str:
    """A range as the equipment tables write it, normal/long in feet."""
    return f"{distance['normal']}/{distance['long']} ft."


def weapon_lines(record: dict[str, Any]) -> list[str]:
    """A weapon's fields that lead to a rule, one line each."""
    lines: list[str] = []
    ranged = record["weapon_range"] == "Ranged"
    lines.append(
        f"Category: {record['weapon_category']} {record['weapon_range'].lower()} weapon"
    )

    damage: dict[str, Any] | None = record.get("damage")
    if damage:
        text = f"{damage['damage_dice']} {damage['damage_type']['name'].lower()}"
        versatile: dict[str, Any] | None = record.get("two_handed_damage")
        if versatile:
            text += f" ({versatile['damage_dice']} two-handed)"
        lines.append(f"Damage: {text}")
    else:
        lines.append("Damage: none")

    names = [prop["name"] for prop in record["properties"]]
    lines.append(f"Properties: {', '.join(names) if names else 'none'}")

    # A melee weapon's range is always 5 in the source, reach or not, so it
    # is left to the Reach property.
    if ranged:
        lines.append(f"Range: {span(record['range'])}")
    thrown: dict[str, int] | None = record.get("throw_range")
    if thrown and not ranged:
        lines.append(f"Thrown range: {span(thrown)}")
    return lines


def armor_lines(record: dict[str, Any]) -> list[str]:
    """A piece of armor's fields that lead to a rule, one line each."""
    lines: list[str] = []
    category: str = record["armor_category"]
    shield = category == "Shield"
    lines.append(f"Category: {category if shield else f'{category} armor'}")

    ac: dict[str, Any] = record["armor_class"]
    if shield:
        armor_class = f"+{ac['base']}"
    elif ac["dex_bonus"] and "max_bonus" in ac:
        armor_class = f"{ac['base']} + Dex modifier (max {ac['max_bonus']})"
    elif ac["dex_bonus"]:
        armor_class = f"{ac['base']} + Dex modifier"
    else:
        armor_class = str(ac["base"])
    lines.append(f"Armor class: {armor_class}")

    strength: int = record["str_minimum"]
    lines.append(f"Strength: {strength if strength else 'none'}")
    stealth = "disadvantage" if record["stealth_disadvantage"] else "no disadvantage"
    lines.append(f"Stealth: {stealth}")
    return lines


def equipment_entries(record: dict[str, Any]) -> list[Entry]:
    """Make the single entry for one weapon or armor; any other equipment makes none."""
    kind: str = record["equipment_category"]["index"]
    if kind not in EQUIPMENT_KINDS:
        return []
    index: str = record["index"]
    name: str = record["name"]
    path = f"equipment > {index}"

    lines = weapon_lines(record) if kind == "weapon" else armor_lines(record)
    blocks: list[str] = [name, "\n".join(lines)]
    special: list[str] | None = record.get("special")
    if special:
        blocks.append("Special. " + "\n\n".join(special))
    text = "\n\n".join(blocks)
    return [Entry(path=path, text=text)]


SOURCES: dict[str, Parser] = {
    SECTIONS_FILE: section_entries,
    CONDITIONS_FILE: condition_entries,
    WEAPON_PROPERTIES_FILE: weapon_property_entries,
    SPELLS_FILE: spell_entries,
    EQUIPMENT_FILE: equipment_entries,
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
