"""Check the supplement's passages word for word against the SRD 5.1 document.

    python scripts/corpus/check_supplement.py <srd.txt>

<srd.txt> is the document's text, written by pdftotext from SRD_CC_v5.1.pdf
(https://media.wizards.com/2023/downloads/dnd/SRD_CC_v5.1.pdf):

    pdftotext -enc UTF-8 SRD_CC_v5.1.pdf srd.txt

The document stays out of the repository; the check needs only its text.

Words are compared lowercased, punctuation and spacing dropped, since the
extracted text breaks hyphens and spaces in ways the document does not. A
paragraph, a new entry's name or an inserted run passes when its words occur
in order, unbroken, on the passage's pages. A table row cannot, since the
extraction reads tables by column, so each cell is checked on its own.

Exits 1 when any passage fails, naming it.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

SUPPLEMENT = (
    Path(__file__).resolve().parents[2] / "data" / "srd-5.1" / "supplement.json"
)


def words(text: str) -> str:
    """The text's words, lowercased and space-separated, with spaces at both ends."""
    text = text.replace("’", "'")
    return " " + " ".join(re.findall(r"[a-z0-9']+", text.lower())) + " "


def cells(table: str) -> list[str]:
    """A markdown table's cells, its separator row left out."""
    found: list[str] = []
    for row in table.splitlines():
        if set(row) <= set("|-"):
            continue
        found += [cell.strip() for cell in row.strip("|").split("|")]
    return found


def pieces(passage: dict[str, Any]) -> list[str]:
    """The runs of text a passage must find in the document."""
    found: list[str] = []
    if passage.get("name"):
        found.append(passage["name"])
    for paragraph in passage["text"]:
        found += cells(paragraph) if paragraph.startswith("|") else [paragraph]
    # A dash cell or one made of nothing a word can match checks nothing.
    return [piece for piece in found if words(piece).strip()]


def main() -> None:
    raw = Path(sys.argv[1]).read_bytes().decode("utf-8", errors="replace")
    pages = raw.split("\f")
    supplement = json.loads(SUPPLEMENT.read_text(encoding="utf-8"))

    failures = 0
    for passage in supplement["passages"]:
        # Each page ends in its footer, which would split a paragraph that
        # runs onto the next page.
        text = (
            "".join(
                words(pages[n - 1]).replace(
                    f" system reference document 5 1 {n} ", " "
                )[:-1]
                for n in passage["pages"]
            )
            + " "
        )
        missing = [p for p in pieces(passage) if words(p) not in text]
        label = f"{passage['op']} {passage['path']} (p. {passage['pages']})"
        if missing:
            failures += 1
            print(f"FAIL {label}")
            for piece in missing:
                print(f"     not found: {piece[:100]}")
        else:
            print(f"ok   {label}")
    total = len(supplement["passages"])
    print(f"{total - failures} of {total} passages found")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
