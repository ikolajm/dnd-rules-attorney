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
FEATURES_FILE = "5e-SRD-Features.json"
RACES_FILE = "5e-SRD-Races.json"
TRAITS_FILE = "5e-SRD-Traits.json"

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
# Every source file's records, by file name.
type Loaded = dict[str, list[dict[str, Any]]]
# A source whose entries need the whole file at once, as class features do to
# merge the records that repeat one text. It is also handed every source file,
# for a fact its own file lacks: a subrace trait names its subrace, and only
# the races say which race that subrace belongs to.
type FileParser = Callable[[list[dict[str, Any]], Loaded], list[Entry]]


def each(parse: Parser) -> FileParser:
    """A file parser running a record parser over every record in turn."""

    def parse_all(records: list[dict[str, Any]], loaded: Loaded) -> list[Entry]:
        return [entry for record in records for entry in parse(record)]

    return parse_all


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


def feature_text(record: dict[str, Any]) -> str:
    """A class feature record's description, the text records are merged on."""
    return "\n\n".join(record["desc"])


def parenthetical(name: str) -> str | None:
    """The trailing parenthetical of a name, Bardic Inspiration (d6)'s d6."""
    match = re.search(r"\s*\(([^)]*)\)$", name)
    return match[1] if match else None


def bare_name(name: str) -> str:
    """A name without its trailing parenthetical."""
    return re.sub(r"\s*\([^)]*\)$", "", name)


def prerequisite(requirement: dict[str, Any]) -> str:
    """One prerequisite as words: a spell, a feature or a level."""
    kind: str = requirement["type"]
    if kind == "level":
        return f"level {requirement['level']}"
    # A spell or a feature is a URL ending in its index.
    index: str = requirement[kind].rsplit("/", 1)[-1]
    return index.replace("-", " ")


def first_record(group: list[dict[str, Any]]) -> dict[str, Any]:
    """The lowest-level record, a "Parent: Option" variant passed over at a tie."""
    return min(group, key=lambda r: (r["level"], ": " in r["name"]))


def feature_scope(group: list[dict[str, Any]]) -> list[str]:
    """The steps above a feature's own: its class and subclass, or none if shared."""
    first = first_record(group)
    if len({r["class"]["index"] for r in group}) > 1:
        return ["class-features"]
    steps = ["class-features", slug(first["class"]["index"])]
    subclass: dict[str, Any] | None = first.get("subclass")
    if subclass:
        steps.append(slug(subclass["index"]))
    return steps


def feature_entry(group: list[dict[str, Any]], name: str) -> Entry:
    """One entry for the records that share a text, its facts kept from their names."""
    first = first_record(group)
    classes = sorted({r["class"]["name"] for r in group})
    subclass: dict[str, Any] | None = first.get("subclass")
    path = " > ".join([*feature_scope(group), slug(name)])

    lines: list[str] = []
    if len(classes) == 1:
        lines.append(f"Class: {classes[0]}")
    else:
        lines.append(f"Classes: {', '.join(classes)}")
    if subclass:
        lines.append(f"Subclass: {subclass['name']}")

    # A level once per distinct level and parenthetical, in level order, so
    # the copies under several classes write each level once.
    levels: list[str] = []
    for record in sorted(group, key=lambda r: r["level"]):
        note = parenthetical(record["name"])
        level = f"{record['level']} ({note})" if note else str(record["level"])
        if level not in levels:
            levels.append(level)
    if len(levels) == 1:
        lines.append(f"Level: {levels[0]}")
    else:
        lines.append(f"Levels: {', '.join(levels)}")

    options = [
        r["name"].split(": ", 1)[1] for r in group if r["name"].startswith(f"{name}: ")
    ]
    if options:
        lines.append(f"Options: {', '.join(options)}")

    requirements: list[dict[str, Any]] = first["prerequisites"]
    if requirements:
        lines.append(
            f"Prerequisite: {'; '.join(prerequisite(r) for r in requirements)}"
        )

    text = "\n\n".join([name, "\n".join(lines), feature_text(first)])
    return Entry(path=path, text=text)


def feature_entries(
    records: list[dict[str, Any]], loaded: Loaded | None = None
) -> list[Entry]:
    """One entry per distinct class feature text, in the file's first-seen order."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        groups.setdefault(feature_text(record), []).append(record)

    # A name drops its parenthetical unless another text in the same scope
    # would then share it, as the cleric's Channel Divinity (1/rest) and its
    # later (2/rest) do; those keep theirs, so no two entries share a path.
    bare = Counter(
        (*feature_scope(g), bare_name(first_record(g)["name"])) for g in groups.values()
    )
    entries: list[Entry] = []
    for group in groups.values():
        full = first_record(group)["name"]
        name = bare_name(full)
        if bare[(*feature_scope(group), name)] > 1:
            name = full
        entries.append(feature_entry(group, name))
    return entries


def names(refs: list[dict[str, Any]]) -> str:
    """The names of referenced records joined by commas, or none."""
    return ", ".join(ref["name"] for ref in refs) or "none"


def race_entries(
    records: list[dict[str, Any]], loaded: Loaded | None = None
) -> list[Entry]:
    """One entry per race: its size, its speed, its traits and its subraces."""
    entries: list[Entry] = []
    for race in records:
        lines = [
            f"Size: {race['size']}",
            f"Speed: {race['speed']} feet",
            f"Traits: {names(race['traits'])}",
        ]
        if race["subraces"]:
            lines.append(f"Subraces: {names(race['subraces'])}")
        text = "\n\n".join([race["name"], "\n".join(lines)])
        entries.append(Entry(path=f"races > {race['index']}", text=text))
    return entries


def breath_option(record: dict[str, Any]) -> str:
    """A Draconic Ancestry color's breath: Black: acid, 30 ft. line, Dex save."""
    specific: dict[str, Any] = record["trait_specific"]
    breath: dict[str, Any] = specific["breath_weapon"]
    area: dict[str, Any] = breath["area_of_effect"]
    save: str = breath["dc"]["dc_type"]["name"].title()
    color = parenthetical(record["name"]) or record["name"]
    damage: str = specific["damage_type"]["name"].lower()
    return f"{color}: {damage}, {area['size']} ft. {area['type']}, {save} save"


def trait_entry(group: list[dict[str, Any]], subrace_race: dict[str, Any]) -> Entry:
    """One entry for the trait records that share a text."""
    # The parent record names the entry; its colored variants are options.
    first = min(group, key=lambda r: "parent" in r)
    races = sorted({race["name"] for r in group for race in r["races"]})
    subraces = {s["index"]: s for r in group for s in r["subraces"]}

    lines: list[str] = []
    steps = ["racial-traits"]
    if subraces:
        # A subrace trait names no race of its own; its subrace's race is it.
        (subrace,) = subraces.values()
        race = subrace_race[subrace["index"]]
        steps += [race["index"], subrace["index"]]
        lines += [f"Race: {race['name']}", f"Subrace: {subrace['name']}"]
    elif len(races) == 1:
        steps.append(slug(first["races"][0]["index"]))
        lines.append(f"Race: {races[0]}")
    else:
        lines.append(f"Races: {', '.join(races)}")
    steps.append(slug(first["name"]))

    options = [breath_option(r) for r in group if "parent" in r]
    if options:
        lines.append(f"Options: {'; '.join(options)}")

    text = "\n\n".join([first["name"], "\n".join(lines), "\n\n".join(first["desc"])])
    return Entry(path=" > ".join(steps), text=text)


def trait_entries(records: list[dict[str, Any]], loaded: Loaded) -> list[Entry]:
    """One entry per distinct racial trait text, in the file's first-seen order."""
    subrace_race = {
        subrace["index"]: race
        for race in loaded[RACES_FILE]
        for subrace in race["subraces"]
    }
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        groups.setdefault("\n\n".join(record["desc"]), []).append(record)
    return [trait_entry(group, subrace_race) for group in groups.values()]


SOURCES: dict[str, FileParser] = {
    SECTIONS_FILE: each(section_entries),
    CONDITIONS_FILE: each(condition_entries),
    WEAPON_PROPERTIES_FILE: each(weapon_property_entries),
    SPELLS_FILE: each(spell_entries),
    EQUIPMENT_FILE: each(equipment_entries),
    FEATURES_FILE: feature_entries,
    RACES_FILE: race_entries,
    TRAITS_FILE: trait_entries,
}


def load_corpus(data_dir: Path) -> list[Entry]:
    """Read every source file, refusing duplicate paths."""
    loaded: Loaded = {
        name: json.loads((data_dir / name).read_text(encoding="utf-8"))
        for name in SOURCES
    }
    entries: list[Entry] = []
    for name, parse in SOURCES.items():
        entries.extend(parse(loaded[name], loaded))

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
