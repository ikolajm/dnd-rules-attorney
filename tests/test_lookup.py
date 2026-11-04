"""Tests for linking the records a question names ahead of retrieval's order."""

from rules_attorney.corpus import Entry
from rules_attorney.lookup import links, lookup_order, name_index


def test_a_name_inside_a_longer_word_does_not_link() -> None:
    entry = Entry("spells > light", "Light\n\nA bright light.")
    index = name_index([entry], ("spells",))
    assert links("Does Call Lightning need concentration?", index) == []


def test_a_plural_links_its_record() -> None:
    entry = Entry("equipment > dagger", "Dagger\n\nFinesse, light, thrown.")
    index = name_index([entry], ("equipment",))
    assert links("Can I throw two daggers?", index) == ["equipment > dagger"]


def test_a_linked_record_past_ten_lands_in_the_ten() -> None:
    ranking = [f"r{n}" for n in range(20)]
    order = lookup_order(["r15"], ranking, 10)
    assert len(order) == 10
    assert order[0] == "r15"


def test_more_than_ten_links_hand_over_ten() -> None:
    linked = [f"l{n}" for n in range(12)]
    assert len(lookup_order(linked, [], 10)) == 10
