# Lazy-dunmas (DnD Rules Attorney)

Rules disputes at a D&D table, answered by a local model from the SRD 5.1, every ruling citing the sections it rests on, plus an evaluation harness that measures retrieval and answers separately against a gold set.

<!-- Demo video and screenshots go here. -->

## How it works

You ask one rules question, and the screen shows the run in the order it happens:

1. **Question.** A gate call first decides whether the question is about the rules of D&D 5e at all. A question off the game is refused and handed back to edit; a question that might be about the rules goes on.
2. **Splitting the dispute.** The model names the separate rules the question turns on, one short sub-question per rule.
3. **Rules found.** The question and each sub-question are embedded and ranked against every SRD entry by cosine similarity, and the rankings are fused into one. The first ten entries are what the model is handed.
4. **Verdict.** The model rules from those ten entries alone and returns a structured ruling: the verdict, an ambiguity flag, an explanation, and the entries it cites. Each cited entry opens its source text beside the ruling.

This is level 3 below. The server streams each phase to the screen as server-sent events as it lands. A stop cancels the request to the model, and a run is ended at 30 seconds.

- **Models:** `qwen3.5:9b` for the gate, the plan and the ruling, and `nomic-embed-text` for the embeddings, both through [Ollama](https://ollama.com), locally.
- **Server:** Python and FastAPI, in `src/rules_attorney/`. The served calls build the same request the measured runs did, so what the screen shows is what the results table measured.
- **Screen:** React and Vite in `web/`, styled with [Loom](https://github.com/ikolajm/loom).
- **Corpus:** the SRD 5.1's rule sections, conditions, spells, weapon properties, weapons, armor and gear with rules, class features and the classes' spellcasting, classes, races, racial traits and feats, from [5e-bits/5e-database](https://github.com/5e-bits/5e-database) at a pinned commit, in `data/srd-5.1/`; and `supplement.json` beside them, the rules only the SRD 5.1 document's prose holds, copied verbatim by hand: multiclassing, the equipment chapter's armor and weapon rules, inspiration, gaining a level, the feats chapter, reaction spell triggers and a few lines more.

## Running it

You need Python 3.12 or later, Node 20.19 or 22.12 or later, and Ollama.

Pull the two models:

```
ollama pull qwen3.5:9b
ollama pull nomic-embed-text
```

Install the server and the screen, from the repository root:

```
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
cd web
npm install
```

On macOS or Linux, the venv's Python is `.venv/bin/python` rather than `.venv/Scripts/python`.

Then, each in a terminal of its own, with Ollama running:

```
.venv/Scripts/python -m uvicorn rules_attorney.server:app
```

```
cd web
npm run dev
```

The server embeds the corpus once at startup, then serves on port 8000. The screen is at `http://localhost:5173`, and forwards questions to the server.

## Results

**Level 1** answers each question from the 10 SRD entries most similar to it: entries chunked by header, embedded with `nomic-embed-text`, ranked by cosine similarity. **Level 3** first has the answering model split the question into sub-questions, one per rule it turns on, ranks the entries for the question and for each sub-question, and fuses the rankings with reciprocal rank fusion; the fused ranking's first 10 entries are handed over, so level 3 gets no more text than level 1. At both levels the model returns a structured ruling (an explanation, an ambiguity flag, a verdict and the entries cited), validated against a Pydantic schema. Scored on the held-out test split, once on the grown corpus: 45 gold items, 37 with a verdict to judge and 10 that should be flagged as ambiguous.

| Model | Level | Thinking | Agreement | Expected flagged | Settled flagged | Schema failures | Cites resolved, strict | Once unmarked |
|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 1 | adaptive | 32 / 37 | 4 / 10 | 0 / 35 | 0 / 45 | 109 / 109 | 109 / 109 |
| claude-opus-5-5 | 3 | adaptive | 33 / 37 | 4 / 10 | 0 / 35 | 0 / 45 | 110 / 110 | 110 / 110 |
| gemma4:12b | 1 | off | 28 / 37 | 1 / 10 | 10 / 35 | 1 / 45 | 65 / 77 | 65 / 77 |
| qwen3.5:9b | 1 | off | 32 / 37 | 1 / 10 | 3 / 35 | 0 / 45 | 74 / 78 | 77 / 78 |
| qwen3.5:9b | 3 | off | 28 / 37 | 1 / 10 | 3 / 35 | 2 / 45 | 69 / 76 | 76 / 76 |
| qwen3.5:4b | 1 | off | 29 / 37 | 1 / 10 | 6 / 35 | 3 / 45 | 50 / 67 | 58 / 67 |
| qwen3.5:2b | 1 | off | 27 / 37 | 1 / 10 | 4 / 35 | 0 / 45 | 1 / 62 | 59 / 62 |
| qwen3.5:0.8b | 1 | off | 17 / 37 | 4 / 10 | 9 / 35 | 1 / 45 | 11 / 52 | 14 / 52 |
| ministral-3:8b | 1 | off | 28 / 37 | 2 / 10 | 18 / 35 | 0 / 45 | 18 / 80 | 56 / 80 |
| olmo-3:7b-instruct | 1 | off | 17 / 37 | 3 / 10 | 13 / 35 | 0 / 45 | 37 / 64 | 54 / 64 |
| floor | - | - | 18 / 37 | 0 / 10 | 0 / 35 | 0 / 45 | 0 / 0 | 0 / 0 |

- **Agreement** is whether the verdict means the same as the gold verdict, decided by Claude Sonnet 5.5 as judge. The judge was checked against hand grades before its scores were counted, and matched twelve of twelve graded blind.
- **The flag** is read as two rates, never one count: a system that never flags would score well on a count, since settled items outnumber the rest.
- **Cites** are checked against the corpus as written and once a leading `## ` marker, the commonest slip, is removed.
- **The floor** answers "no" to every item, never flags and cites nothing, judged like any other row, so the bottom of the table is measured.
- **Local models** run through Ollama as their default tags ship them, `Q4_K_M` except `qwen3.5:2b` and `qwen3.5:0.8b` at `Q8_0`, with thinking off and temperature 0. **Opus 5.5** is the ceiling, through the API at effort `high`; it cannot turn thinking off.
- With 37 judged items, one item is about 2.7 points, and a gap of one between rows is not a finding. Agreement does not separate the top three; the ceiling separates on the flag and on cites.
- **Level 3 gives Opus one verdict and costs `qwen3.5:9b` four.** Opus gains two and loses one. The 9b gains one and loses five, two of the five its schema failures: explanations that argued both readings until they reached the 4,096-token cap. On dev the 9b loses four too, 39 to 35 of 54. The loop is not level 3's alone: on dev the 9b hit the cap once at each level. The planning call adds about 160 seconds across the 45 items for Opus and 25 for the 9b.

Retrieval on the same test items, scored against the entries each gold item cites:

| k | recall@k, level 1 | all-cites@k, level 1 | all-cites@k, level 3 planned by `qwen3.5:9b` | all-cites@k, level 3 planned by Opus |
|---|---|---|---|---|
| 3 | 0.650 | 0.333 | 0.222 | 0.333 |
| 5 | 0.733 | 0.444 | 0.400 | 0.467 |
| 10 | 0.839 | 0.600 | 0.489 | 0.667 |
| 20 | 0.909 | 0.778 | 0.689 | - |

recall@k is the share of an item's cited entries in the top k; all-cites@k is the share of items with every cited entry there. At the k the model is handed, two items in five are missing an entry their ruling needs. Most of that is the items the grown corpus brought: the 28 earlier items complete 21 at 10 on their earlier cites, as before the corpus grew, and 19 with two of them re-cited to a class feature, while the 17 new items complete 8, most misses a short weapon entry or the size rule. Splitting the question helps when the planner decomposes and costs when it rephrases: Opus gives no sub-questions for 16 of 45 items and two to four for the rest, gaining three items at 10, while the 9b gives one for 37, most of them a rephrasing of the question, and loses five. Opus's level 3 column is counted from its answer run's records, which hold the 10 entries handed over, so it stops at 10.

Every other number is computed from run records by `scripts/summarize_runs.py --table`, `scripts/eval_retrieval.py --split test` and `scripts/eval_multihop.py --split test`, all at commit `62538c6`.

## Reproducing the results

The gold set is `gold/gold.json`, each item a question, its expected verdict, whether it is settled or ambiguous, and the entries its ruling cites, split into dev and test. Tuning happens on dev; test is scored once. The scripts that run a split take `--split test` for the test split and run dev without it. Those that write records write them to `runs/`, which git ignores, each record carrying the commit it ran at and whether the tree was dirty.

| Script | What it does |
|---|---|
| `scripts/eval_retrieval.py` | Scores level 1's retrieval: recall@k and all-cites@k |
| `scripts/eval_multihop.py <model>` | Plans with the model named and scores level 3's fused retrieval |
| `scripts/answer_dev.py <model> [--level 1\|3]` | Rules on every item of the split; a model named `claude-…` answers through the API |
| `scripts/judge_dev.py runs/<run>.jsonl` | Judges a run's verdicts and flags with Claude Sonnet 5.5 |
| `scripts/floor_dev.py` | Writes the floor row: "no" to every item, no flag, no cites |
| `scripts/summarize_runs.py --table runs/<run>.jsonl ...` | Prints the results table from judged runs |
| `scripts/check_gate.py <model>` | Runs the gate over the gold questions and `gold/gate-refusals.json`, a set it must refuse |
| `scripts/check_stream.py <id> ...` | Posts gold items to the running server and checks each matches its measured record |
| `scripts/check_supplement.py <srd.txt>` | Checks every passage in `supplement.json` word for word against the SRD 5.1 document's text |

The judge and the hosted rows call the Claude API and authenticate with the profile `ant auth login` stores; a set `ANTHROPIC_API_KEY` takes precedence over it, even an empty one. Everything else runs locally. `scripts/pull_srd.py` refetches the corpus at its pinned commit.

## Checks

From the repository root:

```
.venv/Scripts/python -m pytest
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m ruff format --check .
.venv/Scripts/python -m mypy
```

From `web/`:

```
npm run build
node --test src/*.test.ts
```

This work includes material taken from the System Reference Document 5.1 ("SRD 5.1") by Wizards of the Coast LLC and available at
https://dnd.wizards.com/resources/systems-reference-document. The SRD 5.1 is licensed under the Creative Commons Attribution 4.0 International License available at https://creativecommons.org/licenses/by/4.0/legalcode.