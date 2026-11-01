"""Tests for building the citable corpus."""

import json
from pathlib import Path
from typing import Any

import pytest

from rules_attorney.corpus import (
    SECTIONS_FILE,
    SOURCES,
    CorpusError,
    armor_lines,
    condition_entries,
    equipment_entries,
    feature_entries,
    load_corpus,
    prerequisite,
    section_entries,
    slug,
    spell_entries,
    weapon_property_entries,
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
    assert entries[1].text == "Child\nchild text"
    assert entries[0].text == "Root Header\nroot text"


def test_spell_entries_renders_a_bare_cantrip() -> None:
    record = {
        "index": "spark",
        "name": "Spark",
        "level": 0,
        "school": {"index": "evocation", "name": "Evocation"},
        "casting_time": "1 action",
        "range": "60 feet",
        "components": ["V", "S"],
        "duration": "Instantaneous",
        "concentration": False,
        "ritual": False,
        "desc": ["First paragraph.", "Second paragraph."],
    }
    entries = spell_entries(record)
    assert [e.path for e in entries] == ["spells > spark"]
    assert entries[0].text == (
        "Spark\n"
        "\n"
        "Level: cantrip\n"
        "School: Evocation\n"
        "Casting time: 1 action\n"
        "Range: 60 feet\n"
        "Components: V, S\n"
        "Duration: Instantaneous\n"
        "Concentration: no\n"
        "Ritual: no\n"
        "\n"
        "First paragraph.\n"
        "\n"
        "Second paragraph."
    )


def test_spell_entries_renders_material_and_higher_levels() -> None:
    record = {
        "index": "salt-ward",
        "name": "Salt Ward",
        "level": 2,
        "school": {"index": "abjuration", "name": "Abjuration"},
        "casting_time": "1 minute",
        "range": "Self",
        "components": ["V", "S", "M"],
        "material": "A pinch of salt.",
        "duration": "Concentration, up to 1 hour",
        "concentration": True,
        "ritual": True,
        "desc": ["Only paragraph."],
        "higher_level": ["The ward grows by 5 feet for each slot level above 2nd."],
    }
    entries = spell_entries(record)
    assert [e.path for e in entries] == ["spells > salt-ward"]
    assert entries[0].text == (
        "Salt Ward\n"
        "\n"
        "Level: 2\n"
        "School: Abjuration\n"
        "Casting time: 1 minute\n"
        "Range: Self\n"
        "Components: V, S, M (A pinch of salt.)\n"
        "Duration: Concentration, up to 1 hour\n"
        "Concentration: yes\n"
        "Ritual: yes\n"
        "\n"
        "Only paragraph.\n"
        "\n"
        "At Higher Levels. The ward grows by 5 feet for each slot level above 2nd."
    )


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
        "spells > fireball",
        "spells > animate-objects",
        "equipment > longsword",
        "equipment > net",
        "equipment > shield",
        "class-features > extra-attack",
        "class-features > fighter > extra-attack",
        "class-features > fighter > champion > improved-critical",
        "class-features > cleric > channel-divinity-1rest",
        "class-features > cleric > channel-divinity-2rest",
    ],
)
def test_committed_corpus_holds_known_paths(path: str) -> None:
    paths = {e.path for e in load_corpus(DATA)}
    assert path in paths


def test_weapon_property_entries_opens_with_its_name() -> None:
    record = {
        "index": "hefty",
        "name": "Hefty",
        "desc": ["First paragraph.", "Second paragraph."],
    }
    entries = weapon_property_entries(record)
    assert [e.path for e in entries] == ["weapon-properties > hefty"]
    assert entries[0].text == "Hefty\n\nFirst paragraph.\n\nSecond paragraph."


def test_condition_entries_opens_with_its_name() -> None:
    record = {
        "index": "dazed",
        "name": "Dazed",
        "desc": ["- First effect.", "- Second effect."],
    }
    entries = condition_entries(record)
    assert [e.path for e in entries] == ["conditions > dazed"]
    assert entries[0].text == "Dazed\n\n- First effect.\n\n- Second effect."


def weapon(**fields: Any) -> dict[str, Any]:
    """A made-up weapon record, its fields overridden by the ones given."""
    record: dict[str, Any] = {
        "index": "war-fork",
        "name": "War Fork",
        "equipment_category": {"index": "weapon", "name": "Weapon"},
        "weapon_category": "Martial",
        "weapon_range": "Melee",
        "damage": {"damage_dice": "1d8", "damage_type": {"name": "Piercing"}},
        "range": {"normal": 5},
        "properties": [],
    }
    record.update(fields)
    return record


def armor(**fields: Any) -> dict[str, Any]:
    """A made-up armor record, its fields overridden by the ones given."""
    record: dict[str, Any] = {
        "index": "bark-mail",
        "name": "Bark Mail",
        "equipment_category": {"index": "armor", "name": "Armor"},
        "armor_category": "Heavy",
        "armor_class": {"base": 15, "dex_bonus": False},
        "str_minimum": 0,
        "stealth_disadvantage": False,
    }
    record.update(fields)
    return record


def test_equipment_entries_renders_a_versatile_thrown_melee_weapon() -> None:
    record = weapon(
        two_handed_damage={"damage_dice": "1d10", "damage_type": {"name": "Piercing"}},
        throw_range={"normal": 20, "long": 60},
        properties=[{"name": "Thrown"}, {"name": "Versatile"}],
    )
    entries = equipment_entries(record)
    assert [e.path for e in entries] == ["equipment > war-fork"]
    assert entries[0].text == (
        "War Fork\n"
        "\n"
        "Category: Martial melee weapon\n"
        "Damage: 1d8 piercing (1d10 two-handed)\n"
        "Properties: Thrown, Versatile\n"
        "Thrown range: 20/60 ft."
    )


def test_equipment_entries_renders_a_ranged_special_weapon_without_damage() -> None:
    record = weapon(
        index="snare",
        name="Snare",
        weapon_range="Ranged",
        range={"normal": 5, "long": 15},
        throw_range={"normal": 5, "long": 15},
        properties=[{"name": "Thrown"}, {"name": "Special"}],
        special=["A creature hit is caught."],
    )
    del record["damage"]
    entries = equipment_entries(record)
    assert entries[0].text == (
        "Snare\n"
        "\n"
        "Category: Martial ranged weapon\n"
        "Damage: none\n"
        "Properties: Thrown, Special\n"
        "Range: 5/15 ft.\n"
        "\n"
        "Special. A creature hit is caught."
    )


def test_equipment_entries_writes_no_range_on_a_melee_weapon() -> None:
    entries = equipment_entries(weapon())
    assert entries[0].text == (
        "War Fork\n"
        "\n"
        "Category: Martial melee weapon\n"
        "Damage: 1d8 piercing\n"
        "Properties: none"
    )


@pytest.mark.parametrize(
    ("category", "armor_class", "expected"),
    [
        ("Light", {"base": 12, "dex_bonus": True}, "12 + Dex modifier"),
        (
            "Medium",
            {"base": 15, "dex_bonus": True, "max_bonus": 2},
            "15 + Dex modifier (max 2)",
        ),
        ("Heavy", {"base": 16, "dex_bonus": False}, "16"),
        ("Shield", {"base": 2, "dex_bonus": False}, "+2"),
    ],
)
def test_armor_lines_writes_each_armor_class_form(
    category: str, armor_class: dict[str, Any], expected: str
) -> None:
    lines = armor_lines(armor(armor_category=category, armor_class=armor_class))
    assert f"Armor class: {expected}" in lines


def test_equipment_entries_renders_heavy_armor() -> None:
    record = armor(str_minimum=13, stealth_disadvantage=True)
    entries = equipment_entries(record)
    assert [e.path for e in entries] == ["equipment > bark-mail"]
    assert entries[0].text == (
        "Bark Mail\n"
        "\n"
        "Category: Heavy armor\n"
        "Armor class: 15\n"
        "Strength: 13\n"
        "Stealth: disadvantage"
    )


def test_equipment_entries_writes_a_shield_and_its_absent_requirements() -> None:
    record = armor(armor_category="Shield", armor_class={"base": 2, "dex_bonus": False})
    lines = armor_lines(record)
    assert lines == [
        "Category: Shield",
        "Armor class: +2",
        "Strength: none",
        "Stealth: no disadvantage",
    ]


def test_equipment_entries_skips_gear() -> None:
    record = {
        "index": "rope-hempen-50-feet",
        "name": "Rope, hempen (50 feet)",
        "equipment_category": {"index": "adventuring-gear", "name": "Adventuring Gear"},
    }
    assert equipment_entries(record) == []


def feature(**fields: Any) -> dict[str, Any]:
    """A made-up class feature record, its fields overridden by the ones given."""
    record: dict[str, Any] = {
        "index": "rally",
        "name": "Rally",
        "class": {"index": "bard", "name": "Bard"},
        "level": 1,
        "prerequisites": [],
        "desc": ["You rally your allies."],
    }
    record.update(fields)
    return record


def test_feature_entries_merges_a_scaling_family() -> None:
    records = [
        feature(index="rally-d6", name="Rally (d6)", level=1),
        feature(index="rally-d8", name="Rally (d8)", level=5),
    ]
    entries = feature_entries(records)
    assert [e.path for e in entries] == ["class-features > bard > rally"]
    assert entries[0].text == (
        "Rally\n\nClass: Bard\nLevels: 1 (d6), 5 (d8)\n\nYou rally your allies."
    )


def test_feature_entries_merges_one_text_across_classes() -> None:
    # "class" is a keyword, so the field goes in by dict unpacking.
    records = [
        feature(**{"class": {"index": "paladin", "name": "Paladin"}}),
        feature(**{"class": {"index": "monk", "name": "Monk"}}),
    ]
    entries = feature_entries(records)
    assert [e.path for e in entries] == ["class-features > rally"]
    assert entries[0].text == (
        "Rally\n\nClasses: Monk, Paladin\nLevel: 1\n\nYou rally your allies."
    )


def test_feature_entries_writes_subclass_options_and_prerequisite() -> None:
    subclass = {"index": "storm", "name": "Storm"}
    # The variant comes first, so the name has to be passed over to its parent's.
    records = [
        feature(name="Ancestor: Red - Fire Damage", subclass=subclass),
        feature(name="Ancestor", subclass=subclass),
        feature(
            index="spark-lance",
            name="Spark Lance",
            level=2,
            desc=["Your bolt reaches farther."],
            prerequisites=[
                {"type": "spell", "spell": "/api/2014/spells/eldritch-blast"}
            ],
        ),
    ]
    entries = feature_entries(records)
    assert [e.path for e in entries] == [
        "class-features > bard > storm > ancestor",
        "class-features > bard > spark-lance",
    ]
    assert entries[0].text == (
        "Ancestor\n"
        "\n"
        "Class: Bard\n"
        "Subclass: Storm\n"
        "Level: 1\n"
        "Options: Red - Fire Damage\n"
        "\n"
        "You rally your allies."
    )
    assert "Prerequisite: eldritch blast" in entries[1].text.splitlines()


def test_feature_entries_keeps_parentheticals_where_names_would_collide() -> None:
    records = [
        feature(name="Rally (1/rest)", level=2),
        feature(name="Rally (2/rest)", level=6, desc=["You rally twice."]),
    ]
    entries = feature_entries(records)
    assert [e.path for e in entries] == [
        "class-features > bard > rally-1rest",
        "class-features > bard > rally-2rest",
    ]
    assert entries[0].text.startswith("Rally (1/rest)\n")


@pytest.mark.parametrize(
    ("requirement", "expected"),
    [
        ({"type": "level", "level": 5}, "level 5"),
        (
            {"type": "spell", "spell": "/api/2014/spells/eldritch-blast"},
            "eldritch blast",
        ),
        (
            {"type": "feature", "feature": "/api/2014/features/pact-of-the-tome"},
            "pact of the tome",
        ),
    ],
)
def test_prerequisite_writes_each_kind(
    requirement: dict[str, Any], expected: str
) -> None:
    assert prerequisite(requirement) == expected
