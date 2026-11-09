"""Tests for building the citable corpus."""

import json
from pathlib import Path
from typing import Any

import pytest

from rules_attorney.corpus import (
    CLASSES_FILE,
    FOCI,
    RACES_FILE,
    SECTIONS_FILE,
    SOURCES,
    SUPPLEMENT_FILE,
    CorpusError,
    Entry,
    Join,
    apply_joins,
    armor_lines,
    class_entries,
    condition_entries,
    equipment_entries,
    feat_entries,
    feature_entries,
    focus_entries,
    item_fields,
    load_corpus,
    magic_item_entries,
    prerequisite,
    race_entries,
    section_entries,
    slug,
    spell_entries,
    spellcasting_joins,
    supplement_joins,
    trait_entries,
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
    supplement: dict[str, list[Any]] = {"passages": []}
    (tmp_path / SUPPLEMENT_FILE).write_text(json.dumps(supplement), encoding="utf-8")
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
        "races > halfling",
        "racial-traits > darkvision",
        "racial-traits > dwarf > hill-dwarf > dwarven-toughness",
        "racial-traits > dragonborn > draconic-ancestry",
        "classes > wizard",
        "class-features > wizard > your-spellbook",
        "feats > grappler",
        "equipment > caltrops",
        "equipment > holy-symbol",
        "beyond-1st-level",
        "multiclassing > class-features > extra-attack",
        "multiclassing > class-features > spellcasting > spell-slots",
        "inspiration",
        "armor > armor-proficiency",
        "weapons > improvised-weapons",
        "feats",
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


def gear(**fields: Any) -> dict[str, Any]:
    """A made-up adventuring gear record, its fields overridden by the ones given."""
    record: dict[str, Any] = {
        "index": "bedroll",
        "name": "Bedroll",
        "equipment_category": {"index": "adventuring-gear", "name": "Adventuring Gear"},
        "desc": ["A roll of blankets."],
    }
    record.update(fields)
    return record


def test_equipment_entries_skips_gear_without_a_rule() -> None:
    assert equipment_entries(gear()) == []


def test_equipment_entries_renders_gear_with_a_rule() -> None:
    record = gear(index="caltrops", name="Caltrops", desc=["Spread them.", "Save."])
    entries = equipment_entries(record)
    assert [e.path for e in entries] == ["equipment > caltrops"]
    assert entries[0].text == "Caltrops\n\nSpread them.\n\nSave."


def foci_records(text: str = "Channel your spells.") -> list[dict[str, Any]]:
    """A gear record for every form of every focus, a focus's forms sharing a text."""
    return [
        gear(index=index, name=index.title(), desc=[f"{name}: {text}"])
        for name, forms in FOCI.items()
        for index in forms
    ]


def test_focus_entries_merges_each_focus_into_one_entry() -> None:
    entries = focus_entries(foci_records())
    assert [e.path for e in entries] == [f"equipment > {slug(name)}" for name in FOCI]
    holy = entries[[*FOCI].index("Holy Symbol")]
    assert holy.text == (
        "Holy Symbol\n\nForms: Amulet, Emblem, Reliquary\n\n"
        "Holy Symbol: Channel your spells."
    )


def test_focus_entries_refuses_forms_whose_texts_differ() -> None:
    records = foci_records()
    amulet = next(r for r in records if r["index"] == "amulet")
    amulet["desc"] = ["Something else."]
    with pytest.raises(CorpusError, match="Holy Symbol"):
        focus_entries(records)


def test_focus_entries_refuses_a_focus_missing_a_form() -> None:
    records = [r for r in foci_records() if r["index"] != "amulet"]
    with pytest.raises(CorpusError, match="Holy Symbol"):
        focus_entries(records)


def proficiency(index: str, name: str) -> dict[str, str]:
    return {"index": index, "name": name}


def test_class_entries_sorts_proficiencies_into_lines() -> None:
    record = {
        "index": "warden",
        "name": "Warden",
        "hit_die": 10,
        "proficiencies": [
            proficiency("light-armor", "Light Armor"),
            proficiency("shields", "Shields"),
            proficiency("simple-weapons", "Simple Weapons"),
            proficiency("crossbows-light", "Crossbows, light"),
            proficiency("herbalism-kit", "Herbalism Kit"),
            proficiency("thieves-tools", "Thieves' Tools"),
            proficiency("saving-throw-str", "Saving Throw: STR"),
        ],
        "saving_throws": [{"index": "str"}, {"index": "wis"}],
    }
    entries = class_entries(record)
    assert [e.path for e in entries] == ["classes > warden"]
    assert entries[0].text == (
        "Warden\n"
        "\n"
        "Hit die: d10\n"
        "Armor: Light Armor; Shields\n"
        "Weapons: Simple Weapons; Crossbows, light\n"
        "Saving throws: Strength, Wisdom"
    )


def test_class_entries_writes_none_for_no_armor() -> None:
    record = {
        "index": "sage",
        "name": "Sage",
        "hit_die": 6,
        "proficiencies": [proficiency("daggers", "Daggers")],
        "saving_throws": [{"index": "int"}],
    }
    assert "Armor: none" in class_entries(record)[0].text


def test_feat_entries_writes_the_prerequisite_before_the_text() -> None:
    record = {
        "index": "brawler",
        "name": "Brawler",
        "prerequisites": [{"ability_score": {"index": "str"}, "minimum_score": 13}],
        "desc": ["You fight well.", "- You hit harder."],
    }
    entries = feat_entries(record)
    assert [e.path for e in entries] == ["feats > brawler"]
    assert entries[0].text == (
        "Brawler\n\nPrerequisite: Strength 13\n\nYou fight well.\n\n- You hit harder."
    )


def test_item_fields_splits_a_line_with_an_attunement_clause() -> None:
    assert item_fields("Wondrous item, rare (requires attunement by a bard)") == [
        "Type: Wondrous item",
        "Rarity: rare",
        "Attunement: requires attunement by a bard",
    ]


def test_item_fields_writes_none_without_an_attunement_clause() -> None:
    assert item_fields("Potion, uncommon") == [
        "Type: Potion",
        "Rarity: uncommon",
        "Attunement: none",
    ]


def test_item_fields_splits_past_a_comma_inside_parentheses() -> None:
    assert item_fields("Armor (light, medium, or heavy), rare") == [
        "Type: Armor (light, medium, or heavy)",
        "Rarity: rare",
        "Attunement: none",
    ]


def test_item_fields_splits_at_the_first_of_several_commas() -> None:
    assert item_fields("Wondrous item, rare (silver), very rare (bronze)") == [
        "Type: Wondrous item",
        "Rarity: rare (silver), very rare (bronze)",
        "Attunement: none",
    ]


def test_item_fields_refuses_a_line_without_a_comma_outside_parentheses() -> None:
    with pytest.raises(CorpusError, match="Ring of odd"):
        item_fields("Ring of odd (rare, cursed)")


def test_item_fields_refuses_two_attunement_clauses() -> None:
    with pytest.raises(CorpusError, match="Ring, rare"):
        item_fields("Ring, rare (requires attunement) (requires attunement by a bard)")


def potion_record() -> dict[str, Any]:
    """A made-up parent whose variants include one named as the parent."""
    return {
        "index": "potion-of-healing",
        "name": "Potion of Healing",
        "variant": False,
        "variants": [
            {"index": "potion-of-healing", "name": "Potion of Healing"},
            {"index": "potion-of-greater-healing", "name": "Potion of Greater Healing"},
            {"index": "weapon-1", "name": "Weapon, +1"},
        ],
        "desc": ["Potion, varies", "You regain hit points.", "| Potion | Rarity |"],
    }


def test_magic_item_entries_writes_the_fields_variants_and_text() -> None:
    entries = magic_item_entries(potion_record())
    assert [e.path for e in entries] == ["magic-items > potion-of-healing"]
    assert entries[0].text == (
        "Potion of Healing\n\n"
        "Type: Potion\nRarity: varies\nAttunement: none\n"
        "Variants: Potion of Greater Healing; Weapon, +1\n\n"
        "You regain hit points.\n\n| Potion | Rarity |"
    )


def test_magic_item_entries_makes_no_entry_for_a_variant() -> None:
    assert magic_item_entries({**potion_record(), "variant": True}) == []


def test_magic_item_entries_writes_no_variants_line_without_variants() -> None:
    entries = magic_item_entries({**potion_record(), "variants": []})
    assert "Variants:" not in entries[0].text


def test_spellcasting_joins_label_each_rule_and_skip_non_casters() -> None:
    def info(name: str, *desc: str) -> dict[str, Any]:
        return {"name": name, "desc": list(desc)}

    loaded: dict[str, list[dict[str, Any]]] = {
        CLASSES_FILE: [
            {"index": "fighter"},
            {
                "index": "wizard",
                "spellcasting": {
                    "info": [
                        info("Ritual Casting", "Cast it slowly."),
                        info("Ability", "Int.", "DC."),
                    ]
                },
            },
            {"index": "warlock", "spellcasting": {"info": [info("Slots", "Few.")]}},
        ]
    }
    assert spellcasting_joins(loaded) == [
        Join(
            "append",
            "class-features > wizard > spellcasting-wizard",
            "***Ritual Casting.*** Cast it slowly.\n\n***Ability.*** Int.\n\nDC.",
        ),
        Join("append", "class-features > warlock > pact-magic", "***Slots.*** Few."),
    ]


def test_supplement_joins_runs_an_insertion_together() -> None:
    supplement = {
        "passages": [
            {
                "op": "insert",
                "path": "a",
                "after": "x",
                "pages": [1],
                "text": ["one", "two"],
            },
            {
                "op": "new",
                "path": "b",
                "name": "B",
                "pages": [1],
                "text": ["one", "two"],
            },
        ]
    }
    assert supplement_joins(supplement) == [
        Join("insert", "a", "onetwo", after="x"),
        Join("new", "b", "one\n\ntwo", name="B"),
    ]


def test_apply_joins_appends_inserts_and_adds_in_order() -> None:
    entries = [Entry("a", "A\n\nCasting time: 1 reaction"), Entry("b", "B")]
    joins = [
        Join("insert", "a", ", when hit", after="Casting time: 1 reaction"),
        Join("append", "b", "More."),
        Join("new", "c", "Rule.", name="C"),
    ]
    assert apply_joins(entries, joins) == [
        Entry("a", "A\n\nCasting time: 1 reaction, when hit"),
        Entry("b", "B\n\nMore."),
        Entry("c", "C\n\nRule."),
    ]


@pytest.mark.parametrize(
    ("join", "message"),
    [
        (Join("append", "missing", "x"), "missing entry: missing"),
        (Join("insert", "a", "x", after="absent"), "one 'absent'"),
        (Join("insert", "a", "x", after="twice"), "one 'twice'"),
        (Join("new", "a", "x", name="A"), "already exists: a"),
        (Join("replace", "a", "x"), "unknown join 'replace'"),
    ],
)
def test_apply_joins_refuses_a_join_that_misses(join: Join, message: str) -> None:
    with pytest.raises(CorpusError, match=message):
        apply_joins([Entry("a", "twice twice")], [join])


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


def ref(index: str, name: str) -> dict[str, str]:
    """A made-up reference to another record, as the source writes one."""
    return {"index": index, "name": name}


# A made-up race with one subrace, as the races file holds it. Only the races
# say which race a subrace belongs to, so the trait tests hand it over too.
MOUNTAINFOLK = {
    "index": "mountainfolk",
    "name": "Mountainfolk",
    "size": "Small",
    "speed": 25,
    "traits": [ref("stone-sense", "Stone Sense")],
    "subraces": [ref("deep-mountainfolk", "Deep Mountainfolk")],
}
LOADED = {RACES_FILE: [MOUNTAINFOLK]}


def trait(**fields: Any) -> dict[str, Any]:
    """A made-up racial trait record, its fields overridden by the ones given."""
    record: dict[str, Any] = {
        "index": "stone-sense",
        "name": "Stone Sense",
        "races": [ref("mountainfolk", "Mountainfolk")],
        "subraces": [],
        "desc": ["You sense stone."],
    }
    record.update(fields)
    return record


def test_race_entries_writes_size_speed_traits_and_subraces() -> None:
    entries = race_entries([MOUNTAINFOLK])
    assert [e.path for e in entries] == ["races > mountainfolk"]
    assert entries[0].text == (
        "Mountainfolk\n"
        "\n"
        "Size: Small\n"
        "Speed: 25 feet\n"
        "Traits: Stone Sense\n"
        "Subraces: Deep Mountainfolk"
    )


def test_race_entries_writes_none_for_a_race_without_traits() -> None:
    plain = {**MOUNTAINFOLK, "traits": [], "subraces": []}
    lines = race_entries([plain])[0].text.splitlines()
    assert "Traits: none" in lines
    assert not any(line.startswith("Subraces:") for line in lines)


def test_trait_entries_cites_a_race_trait_under_its_race() -> None:
    entries = trait_entries([trait()], LOADED)
    assert [e.path for e in entries] == ["racial-traits > mountainfolk > stone-sense"]
    assert entries[0].text == ("Stone Sense\n\nRace: Mountainfolk\n\nYou sense stone.")


def test_trait_entries_cites_a_shared_trait_without_a_race() -> None:
    record = trait(races=[ref("mountainfolk", "Mountainfolk"), ref("dwarf", "Dwarf")])
    entries = trait_entries([record], LOADED)
    assert [e.path for e in entries] == ["racial-traits > stone-sense"]
    assert "Races: Dwarf, Mountainfolk" in entries[0].text.splitlines()


def test_trait_entries_finds_a_subrace_traits_race_in_the_races() -> None:
    record = trait(
        index="deep-sight",
        name="Deep Sight",
        races=[],
        subraces=[ref("deep-mountainfolk", "Deep Mountainfolk")],
    )
    entries = trait_entries([record], LOADED)
    assert [e.path for e in entries] == [
        "racial-traits > mountainfolk > deep-mountainfolk > deep-sight"
    ]
    assert entries[0].text.splitlines()[2:4] == [
        "Race: Mountainfolk",
        "Subrace: Deep Mountainfolk",
    ]


def test_trait_entries_merges_variants_into_options() -> None:
    breath = {
        "area_of_effect": {"size": 15, "type": "cone"},
        "dc": {"dc_type": {"name": "CON"}},
    }
    variant = trait(
        index="ancestry-green",
        name="Ancestry (Green)",
        parent=ref("ancestry", "Ancestry"),
        trait_specific={"damage_type": {"name": "Poison"}, "breath_weapon": breath},
    )
    # The variant comes first, so the name has to be passed over to its parent's.
    entries = trait_entries([variant, trait(index="ancestry", name="Ancestry")], LOADED)
    assert [e.path for e in entries] == ["racial-traits > mountainfolk > ancestry"]
    assert entries[0].text.splitlines()[0] == "Ancestry"
    assert "Options: Green: poison, 15 ft. cone, Con save" in entries[0].text
