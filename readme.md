# DnD Rules Attorney (Lazy-dunmas)

A project to allow local llm to quickly lookup and determine what is legal within the 2014 5e ruleset.

## Results

**Level 1** answers each question from the 10 SRD entries most similar to it: entries chunked by header, embedded with `nomic-embed-text`, ranked by cosine similarity. **Level 3** first has the answering model split the question into sub-questions, one per rule it turns on, ranks the entries for the question and for each sub-question, and fuses the rankings with reciprocal rank fusion; the fused ranking's first 10 entries are handed over, so level 3 gets no more text than level 1. At both levels the model returns a structured ruling (an explanation, an ambiguity flag, a verdict and the entries cited), validated against a Pydantic schema. Scored on the held-out test split, once: 28 gold items, 22 with a verdict to judge and 8 that should be flagged as ambiguous.

| Model | Level | Thinking | Agreement | Expected flagged | Settled flagged | Schema failures | Cites resolved, strict | Once unmarked |
|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 1 | adaptive | 20 / 22 | 4 / 8 | 1 / 20 | 0 / 28 | 66 / 66 | 66 / 66 |
| claude-opus-5-5 | 3 | adaptive | 21 / 22 | 3 / 8 | 0 / 20 | 0 / 28 | 68 / 68 | 68 / 68 |
| gemma4:12b | 1 | off | 19 / 22 | 3 / 8 | 4 / 20 | 0 / 28 | 36 / 47 | 36 / 47 |
| qwen3.5:9b | 1 | off | 20 / 22 | 0 / 8 | 2 / 20 | 0 / 28 | 41 / 47 | 46 / 47 |
| qwen3.5:9b | 3 | off | 18 / 22 | 0 / 8 | 2 / 20 | 1 / 28 | 38 / 44 | 44 / 44 |
| qwen3.5:4b | 1 | off | 18 / 22 | 3 / 8 | 1 / 20 | 2 / 28 | 27 / 38 | 31 / 38 |
| qwen3.5:2b | 1 | off | 14 / 22 | 1 / 8 | 4 / 20 | 0 / 28 | 0 / 37 | 33 / 37 |
| qwen3.5:0.8b | 1 | off | 13 / 22 | 3 / 8 | 7 / 20 | 1 / 28 | 5 / 34 | 7 / 34 |
| ministral-3:8b | 1 | off | 18 / 22 | 5 / 8 | 10 / 20 | 0 / 28 | 26 / 53 | 42 / 53 |
| olmo-3:7b-instruct | 1 | off | 13 / 22 | 5 / 8 | 9 / 20 | 0 / 28 | 17 / 36 | 27 / 36 |
| floor | - | - | 10 / 22 | 0 / 8 | 0 / 20 | 0 / 28 | 0 / 0 | 0 / 0 |

- **Agreement** is whether the verdict means the same as the gold verdict, decided by Claude Sonnet 5.5 as judge. The judge was checked against hand grades before its scores were counted, and matched twelve of twelve graded blind.
- **The flag** is read as two rates, never one count: a system that never flags would score well on a count, since settled items outnumber the rest.
- **Cites** are checked against the corpus as written and once a leading `## ` marker, the commonest slip, is removed.
- **The floor** answers "no" to every item, never flags and cites nothing, judged like any other row, so the bottom of the table is measured.
- **Local models** run through Ollama as their default tags ship them, `Q4_K_M` except `qwen3.5:2b` and `qwen3.5:0.8b` at `Q8_0`, with thinking off and temperature 0. **Opus 5.5** is the ceiling, through the API at effort `high`; it cannot turn thinking off.
- With 22 judged items, one item is about four and a half points, and a gap of one between rows is not a finding. Agreement does not separate the top three; the ceiling separates on the flag and on cites.
- **Level 3 does not separate from level 1.** Opus gains one verdict net and `qwen3.5:9b` loses two: it gains one and loses three, one of the three its schema failure, an explanation that argued both readings until it reached the 4,096-token cap. The 9b looped that way once at level 3 on dev as well, and not at level 1 on either split. The planning call adds about 100 seconds across the 28 items for Opus and 15 for the 9b.

Retrieval on the same test items, scored against the entries each gold item cites:

| k | recall@k, level 1 | all-cites@k, level 1 | all-cites@k, level 3 planned by `qwen3.5:9b` | all-cites@k, level 3 planned by Opus |
|---|---|---|---|---|
| 3 | 0.729 | 0.464 | 0.464 | 0.393 |
| 5 | 0.824 | 0.607 | 0.571 | 0.571 |
| 10 | 0.899 | 0.750 | 0.714 | 0.786 |
| 20 | 0.952 | 0.893 | 0.857 | - |

recall@k is the share of an item's cited entries in the top k; all-cites@k is the share of items with every cited entry there. At the k the model is handed, a quarter of items are missing an entry their ruling needs. Splitting the question moves that by one item either way, and the planner decides which way: the 9b gives one sub-question for 24 of 28 items, most of them a rephrasing of the question, while Opus gives none for 12 and two or three for the rest. Opus's level 3 column is counted from its answer run's records, which hold the 10 entries handed over, so it stops at 10.

Every other number is computed from run records by `scripts/summarize_runs.py --table`, `scripts/eval_retrieval.py --split test` and `scripts/eval_multihop.py --split test`. Level 1's rows are at commit `df178dc` and level 3's at `f9e8a3b`.

This work includes material taken from the System Reference Document 5.1 ("SRD 5.1") by Wizards of the Coast LLC and available at
https://dnd.wizards.com/resources/systems-reference-document. The SRD 5.1 is licensed under the Creative Commons Attribution 4.0 International License available at https://creativecommons.org/licenses/by/4.0/legalcode.