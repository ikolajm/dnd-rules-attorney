"""Pull the SRD 5.1 source files into data/srd-5.1/.

The files are the 2014 English data from the 5e-bits/5e-database repository on
GitHub, fetched at the commit pinned in COMMIT and written unchanged. To move
the corpus to a newer source, change COMMIT, rerun this script, and read the
diff under data/srd-5.1/ to see what the source changed.
"""

from pathlib import Path
from urllib.request import urlopen

from rules_attorney.corpus import (
    SOURCES,
    load_corpus,
    render_markdown,
)

COMMIT: str = "a6212beb4b278917c2cff41c2b04c4ef4f3e0d6f"
BASE: str = (
    f"https://raw.githubusercontent.com/5e-bits/5e-database/{COMMIT}/src/2014/en/"
)

OUT = Path(__file__).resolve().parent.parent / "data" / "srd-5.1"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name in SOURCES:
        with urlopen(BASE + name) as resp:
            body = resp.read()
        (OUT / name).write_bytes(body)

    entries = load_corpus(OUT)
    markdown = render_markdown(entries)
    (OUT / "corpus.md").write_text(markdown + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
