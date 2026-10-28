"""A run's scores computed from its records, and the published table built from them."""

from dataclasses import dataclass
from typing import Any

from rules_attorney.answer import unmarked


@dataclass(frozen=True)
class Row:
    """One run's scores, read from its records and its judged file."""

    model: str
    # False on the local rows, "adaptive" on the hosted one, None on the floor.
    think: bool | str | None
    commit: str
    dirty: bool
    items: int
    failed: list[str]
    agreed: int
    judged: int
    # The flag as two rates, never one count of flags right: settled items
    # outnumber the rest, so a system that never flags scores well on a count.
    expected_flagged: int
    expected: int
    settled_flagged: int
    settled: int
    cites: int
    strict: int
    grounded: int
    seconds_max: float
    seconds_total: float


def build_row(
    records: list[dict[str, Any]],
    judged: dict[str, dict[str, Any]],
    known: set[str],
) -> Row:
    """The scores of one run, its judged records keyed by item id."""
    config = records[0]["config"]
    ok = [record for record in records if record["ruling"] is not None]

    sent = [j for j in judged.values() if j["judged"]]

    def flagged(settled: bool) -> tuple[int, int]:
        # A failed answer has no flag, so it counts as unflagged in its status.
        rows = [
            r for r in records if (judged[r["id"]]["status"] == "settled") == settled
        ]
        hits = sum(
            1 for r in rows if r["ruling"] is not None and r["ruling"]["ambiguous"]
        )
        return hits, len(rows)

    expected_flagged, expected = flagged(False)
    settled_flagged, settled = flagged(True)
    cites = [cite for record in ok for cite in record["ruling"]["cites"]]
    seconds = [record["seconds"] for record in records]

    return Row(
        model=config["model"],
        think=config.get("think"),
        commit=config["commit"],
        dirty=config["dirty"],
        items=len(records),
        failed=[record["id"] for record in records if record["ruling"] is None],
        agreed=sum(1 for j in sent if j["agrees"]),
        judged=len(sent),
        expected_flagged=expected_flagged,
        expected=expected,
        settled_flagged=settled_flagged,
        settled=settled,
        cites=len(cites),
        strict=sum(1 for cite in cites if cite in known),
        grounded=sum(1 for cite in unmarked(cites) if cite in known),
        seconds_max=max(seconds),
        seconds_total=sum(seconds),
    )


HEADER = (
    "| Model | Thinking | Agreement | Expected flagged | Settled flagged "
    "| Schema failures | Cites resolved, strict | Once unmarked | Commit |"
)
RULE = "|---|---|---|---|---|---|---|---|---|"


def thinking(think: bool | str | None) -> str:
    """The thinking column: off, the mode a hosted row runs, or a dash for none."""
    if think is None:
        return "-"
    if think is False:
        return "off"
    return str(think)


def markdown_row(row: Row) -> str:
    """One run as a row of the published table."""
    commit = row.commit[:7] + (" dirty" if row.dirty else "")
    cells = [
        row.model,
        thinking(row.think),
        f"{row.agreed} / {row.judged}",
        f"{row.expected_flagged} / {row.expected}",
        f"{row.settled_flagged} / {row.settled}",
        f"{len(row.failed)} / {row.items}",
        f"{row.strict} / {row.cites}",
        f"{row.grounded} / {row.cites}",
        commit,
    ]
    return "| " + " | ".join(cells) + " |"


def markdown_table(rows: list[Row]) -> str:
    """The published table, one row per run in the order given."""
    return "\n".join([HEADER, RULE, *(markdown_row(row) for row in rows)])
