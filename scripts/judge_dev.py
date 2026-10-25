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
    # Flags right over every record. A failed answer has no flag, so it is
    # wrong here but neither a miss nor a false flag.
    flags_right = 0
    flag_misses = 0
    false_flags = 0
    tokens_in = 0
    tokens_out = 0

    with out.open("w", encoding="utf-8") as file:
        for record in records:
            item = gold[record["id"]]
            status = item["status"]
            # The system's ruling, None when its answer failed the schema.
            answer = record["ruling"]

            flag_ok = answer is not None and flag_correct(status, answer["ambiguous"])
            if flag_ok:
                flags_right += 1
            elif answer is not None and status == "settled":
                false_flags += 1
            elif answer is not None:
                flag_misses += 1

            agrees: bool | None = None
            reason: str | None = None
            reply: str | None = None
            usage: dict[str, int] | None = None
            if needs_judge(status):
                judged += 1
                if answer is None:
                    # Nothing to judge, and it does not agree.
                    unanswered += 1
                    agrees = False
                else:
                    prompt = build_judge_prompt(
                        item["question"],
                        item["verdict"],
                        item["ruling"],
                        answer["verdict"],
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
    print(f"flags right: {flags_right} / {len(records)}")
    print(f"  misses: {flag_misses}, false flags: {false_flags}")
    print(f"tokens: {tokens_in} in, {tokens_out} out")


if __name__ == "__main__":
    main()
