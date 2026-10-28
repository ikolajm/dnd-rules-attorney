# DnD Rules Attorney (Lazy-dunmas)

A project to allow local llm to quickly lookup and determine what is legal within the 2014 5e ruleset.

## Results: single-shot retrieval

Each question is answered from the 10 SRD entries most similar to it: entries chunked by header, embedded with `nomic-embed-text`, ranked by cosine similarity. The model returns a structured ruling (an explanation, an ambiguity flag, a verdict and the entries cited), validated against a Pydantic schema. Scored on the held-out test split, once: 28 gold items, 22 with a verdict to judge and 8 that should be flagged as ambiguous.

| Model | Thinking | Agreement | Expected flagged | Settled flagged | Schema failures | Cites resolved, strict | Once unmarked |
|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | adaptive | 20 / 22 | 4 / 8 | 1 / 20 | 0 / 28 | 66 / 66 | 66 / 66 |
| gemma4:12b | off | 19 / 22 | 3 / 8 | 4 / 20 | 0 / 28 | 36 / 47 | 36 / 47 |
| qwen3.5:9b | off | 20 / 22 | 0 / 8 | 2 / 20 | 0 / 28 | 41 / 47 | 46 / 47 |
| qwen3.5:4b | off | 18 / 22 | 3 / 8 | 1 / 20 | 2 / 28 | 27 / 38 | 31 / 38 |
| qwen3.5:2b | off | 14 / 22 | 1 / 8 | 4 / 20 | 0 / 28 | 0 / 37 | 33 / 37 |
| qwen3.5:0.8b | off | 13 / 22 | 3 / 8 | 7 / 20 | 1 / 28 | 5 / 34 | 7 / 34 |
| ministral-3:8b | off | 18 / 22 | 5 / 8 | 10 / 20 | 0 / 28 | 26 / 53 | 42 / 53 |
| olmo-3:7b-instruct | off | 13 / 22 | 5 / 8 | 9 / 20 | 0 / 28 | 17 / 36 | 27 / 36 |
| floor | - | 10 / 22 | 0 / 8 | 0 / 20 | 0 / 28 | 0 / 0 | 0 / 0 |

- **Agreement** is whether the verdict means the same as the gold verdict, decided by Claude Sonnet 5.5 as judge. The judge was checked against hand grades before its scores were counted, and matched twelve of twelve graded blind.
- **The flag** is read as two rates, never one count: a system that never flags would score well on a count, since settled items outnumber the rest.
- **Cites** are checked against the corpus as written and once a leading `## ` marker, the commonest slip, is removed.
- **The floor** answers "no" to every item, never flags and cites nothing, judged like any other row, so the bottom of the table is measured.
- **Local models** run through Ollama as their default tags ship them, `Q4_K_M` except `qwen3.5:2b` and `qwen3.5:0.8b` at `Q8_0`, with thinking off and temperature 0. **Opus 5.5** is the ceiling, through the API at effort `high`; it cannot turn thinking off.
- With 22 judged items, one item is about four and a half points, and a gap of one between rows is not a finding. Agreement does not separate the top three; the ceiling separates on the flag and on cites.

Retrieval on the same test items, scored against the entries each gold item cites:

| k | recall@k | all-cites@k |
|---|---|---|
| 3 | 0.729 | 0.464 |
| 5 | 0.824 | 0.607 |
| 10 | 0.899 | 0.750 |
| 20 | 0.952 | 0.893 |

recall@k is the share of an item's cited entries in the top k; all-cites@k is the share of items with every cited entry there. At the k the model is handed, a quarter of items are missing an entry their ruling needs. Multi-hop retrieval, splitting a dispute into sub-questions retrieved for separately, is the next level, scored against this table on the same items.

Every number is computed from run records by `scripts/summarize_runs.py --table` and `scripts/eval_retrieval.py --split test`, at commit `df178dc`.

This work includes material taken from the System Reference Document 5.1 ("SRD 5.1") by Wizards of the Coast LLC and available at
https://dnd.wizards.com/resources/systems-reference-document. The SRD 5.1 is licensed under the Creative Commons Attribution 4.0 International License available at https://creativecommons.org/licenses/by/4.0/legalcode.