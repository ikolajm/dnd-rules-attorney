"""Judges a dev run's records for verdict agreement and the flag.

Calls the live Claude API.
"""

import json
import sys
from pathlib import Path
from typing import Any

from rules_attorney.judge import (
    JUDGE_INSTRUCTIONS,
    JUDGE_MODEL,
    MAX_TOKENS,
    build_judge_prompt,
    claude_judge,
    flag_correct,
    needs_judge,
    parse_judgement,
    reply_text,
)
from rules_attorney.provenance import commit

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "gold" / "gold.json"


def main() -> None:
    """Score each record of the run named on the command line."""
    run = Path(sys.argv[1])
    gold: dict[str, dict[str, Any]] = {
        item["id"]: item for item in json.loads(GOLD.read_text(encoding="utf-8"))
    }
    records: list[dict[str, Any]] = [
        json.loads(line) for line in run.open(encoding="utf-8")
    ]
    source = commit(ROOT)
    config: dict[str, Any] = {
        "judge_model": JUDGE_MODEL,
        "max_tokens": MAX_TOKENS,
        "instructions": JUDGE_INSTRUCTIONS,
        "run": run.name,
        "commit": source["commit"],
        "dirty": source["dirty"],
    }
    out = run.with_name(f"{run.stem}.judged-{JUDGE_MODEL}.jsonl")

    # Items sent toward the judge, and those it agreed with.
    judged = 0
    agreed = 0
    # Answers that failed their own schema, so no call was made.
    unanswered = 0
    # Judge replies that did not parse.
    judge_failures = 0
    # The flag as two rates, never one count of flags right: settled items
    # outnumber the rest, so a model that never flags scores well on a count.
    # A failed reply has no flag, so it counts as unflagged in its status.
    expected_total = 0
    expected_flagged = 0
    settled_total = 0
    settled_flagged = 0
    tokens_in = 0
    tokens_out = 0

    with out.open("w", encoding="utf-8") as file:
        for record in records:
            item = gold[record["id"]]
            status = item["status"]
            # The system's ruling, None when the reply failed the schema.
            ruling = record["ruling"]

            flag_ok = ruling is not None and flag_correct(status, ruling["ambiguous"])
            flagged = ruling is not None and ruling["ambiguous"]
            if status == "settled":
                settled_total += 1
                if flagged:
                    settled_flagged += 1
            else:
                expected_total += 1
                if flagged:
                    expected_flagged += 1

            agrees: bool | None = None
            reason: str | None = None
            reply: str | None = None
            usage: dict[str, int] | None = None
            if needs_judge(status):
                judged += 1
                if ruling is None:
                    # Nothing to judge, and it does not agree.
                    unanswered += 1
                    agrees = False
                else:
                    prompt = build_judge_prompt(
                        item["question"],
                        item["verdict"],
                        item["ruling"],
                        ruling["answer"]["verdict"],
                    )
                    message = claude_judge(prompt)
                    reply = reply_text(message)
                    usage = {
                        "input_tokens": message.usage.input_tokens,
                        "output_tokens": message.usage.output_tokens,
                    }
                    tokens_in += usage["input_tokens"]
                    tokens_out += usage["output_tokens"]
                    judgement = parse_judgement(reply)
                    if judgement is None:
                        # Counted, never retried, and never an agreement.
                        judge_failures += 1
                    else:
                        agrees = judgement.agrees
                        reason = judgement.reason
                        if agrees:
                            agreed += 1

            scored = {
                "id": record["id"],
                "status": status,
                "flag_ok": flag_ok,
                "judged": needs_judge(status),
                "agrees": agrees,
                "reason": reason,
                "reply": reply,
                "usage": usage,
                "config": config,
            }
            file.write(json.dumps(scored) + "\n")
            print(f"{record['id']}: agrees={agrees} flag_ok={flag_ok}")

    print(out)
    print(f"verdict agreement: {agreed} / {judged}")
    print(f"  answers that failed their schema: {unanswered}")
    print(f"  judge replies that did not parse: {judge_failures}")
    print(f"expected items flagged: {expected_flagged} / {expected_total}")
    print(f"settled items flagged: {settled_flagged} / {settled_total}")
    print(f"tokens: {tokens_in} in, {tokens_out} out")


if __name__ == "__main__":
    main()
