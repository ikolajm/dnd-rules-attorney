"""Links the records a question names, ahead of retrieval's order."""

import re

from rules_attorney.corpus import Entry

# The path roots a name links from. The dev runs choose the set: a class or
# race name more often describes the character than carries the ruling.
KINDS: tuple[str, ...] = (
    "equipment",
    "spells",
    "conditions",
    "weapon-properties",
    "feats",
    "classes",
    "races",
    "class-features",
    "racial-traits",
)


def name_index(entries: list[Entry], kinds: tuple[str, ...]) -> dict[str, list[str]]:
    """Maps each lowercased name to the paths of the records of a kind it names."""
    index: dict[str, list[str]] = {}
    for entry in entries:
        root = entry.path.split(" > ")[0]
        if root in kinds:
            name = entry.text.split("\n")[0].lower()
            index.setdefault(name, []).append(entry.path)
    return index


def links(question: str, index: dict[str, list[str]]) -> list[str]:
    """Returns the paths the question names, in the order the names appear."""
    text = question.lower()
    found: list[tuple[int, str]] = []
    for name in index:
        pattern = rf"\b{re.escape(name)}s?\b"
        match = re.search(pattern, text)
        if match is not None:
            found.append((match.start(), name))
    linked: list[str] = []
    for _start, name in sorted(found):
        linked.extend(index[name])
    return linked


def lookup_order(linked: list[str], ranking: list[str], k: int) -> list[str]:
    """Returns the linked paths, then the ranking, each path once, cut to k."""
    joined = linked + ranking
    unique = list(dict.fromkeys(joined))
    return unique[:k]
