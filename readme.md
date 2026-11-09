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
- **Server:** Python and FastAPI, in `src/rules_attorney/app/`. The served calls build the same request the measured runs did, so what the screen shows is what the results table measured.
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
.venv/Scripts/python -m uvicorn rules_attorney.app.server:app
```

```
cd web
npm run dev
```

The server embeds the corpus once at startup, then serves on port 8000. The screen is at `http://localhost:5173`, and forwards questions to the server.

## Results

Every stage hands the answering model 10 SRD entries, so none wins by reading more.

- **Level 1** ranks the entries, chunked by header and embedded with `nomic-embed-text`, by cosine similarity to the question.
- **1 + rerank** reorders level 1's top 30 with the cross-encoder `BAAI/bge-reranker-v2-m3` and fuses that order with level 1's.
- **1 + lookup** puts the records the question names, a weapon, a spell, a condition, a race, a class feature, a magic item or a creature, ahead of level 1's order.
- **Level 3** has the answering model split the question into sub-questions, one per rule it turns on, ranks the entries for the question and each sub-question, and fuses the rankings with reciprocal rank fusion, each cut to its first 10.
- **The loop** gives the answering model two tools, `search`, which returns the top five entries in full, and `lookup`, which resolves a record by name, for up to six calls. The code then hands over the records looked up first, then the question's ranking fused with every search's, each cut to its first 10.

At every stage the model returns a structured ruling (an explanation, an ambiguity flag, a verdict and the entries cited), validated against a Pydantic schema. Scored on the held-out test split once: 52 gold items, 44 with a verdict to judge and 10 that should be flagged as ambiguous.

### Retrieval

all-cites@k, the share of items with every entry their ruling cites in the top k:

| k | level 1 | 1 + rerank | 1 + lookup | level 3, `qwen3.5:9b` | level 3, Opus | loop, `qwen3.5:9b` | loop, Opus |
|---|---|---|---|---|---|---|---|
| 3 | 0.327 | 0.346 | 0.404 | 0.250 | 0.346 | 0.404 | 0.423 |
| 5 | 0.423 | 0.462 | 0.577 | 0.423 | 0.538 | 0.500 | 0.712 |
| 10 | 0.558 | 0.596 | 0.654 | 0.538 | 0.692 | 0.654 | 0.904 |

At the 10 the model is handed, level 1 completes 56% of items and Opus's loop 90%. The loop driven by `qwen3.5:9b` scores 0.654, the same as the lookup alone, and level 3 planned by the 9b scores below level 1 at 3 and 10. Retrieval is deterministic for level 1, rerank and lookup; level 3 and the loop depend on the model's plans and searches, and each column is the one draw the answers below were given.

### Rulings

| Model | Level | Thinking | Agreement | Expected flagged | Settled flagged | Schema failures | Cites resolved, strict | Once unmarked | Commit |
|---|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 1 | adaptive | 38 / 44 | 5 / 10 | 0 / 42 | 0 / 52 | 129 / 129 | 129 / 129 | 15463d8 |
| claude-opus-5-5 | 1 + rerank | adaptive | 37 / 44 | 3 / 10 | 0 / 42 | 0 / 52 | 127 / 127 | 127 / 127 | 15463d8 |
| claude-opus-5-5 | 1 + lookup | adaptive | 39 / 44 | 4 / 10 | 0 / 42 | 0 / 52 | 137 / 137 | 137 / 137 | 15463d8 |
| claude-opus-5-5 | 3 | adaptive | 40 / 44 | 3 / 10 | 0 / 42 | 0 / 52 | 138 / 138 | 138 / 138 | 15463d8 |
| claude-opus-5-5 | loop | adaptive | 43 / 44 | 3 / 10 | 1 / 42 | 0 / 52 | 165 / 165 | 165 / 165 | 15463d8 |
| gemma4:12b | 1 | off | 32 / 44 | 2 / 10 | 16 / 42 | 2 / 52 | 80 / 93 | 80 / 93 | 15463d8 |
| qwen3.5:9b | 1 | off | 32 / 44 | 1 / 10 | 5 / 42 | 1 / 52 | 79 / 87 | 86 / 87 | 15463d8 |
| qwen3.5:9b | 1 + rerank | off | 35 / 44 | 0 / 10 | 4 / 42 | 0 / 52 | 72 / 83 | 79 / 83 | 15463d8 |
| qwen3.5:9b | 1 + lookup | off | 36 / 44 | 0 / 10 | 6 / 42 | 0 / 52 | 66 / 94 | 91 / 94 | 15463d8 |
| qwen3.5:9b | 3 | off | 33 / 44 | 0 / 10 | 1 / 42 | 1 / 52 | 77 / 88 | 87 / 88 | 15463d8 |
| qwen3.5:9b | loop | off | 31 / 44 | 0 / 10 | 4 / 42 | 0 / 52 | 85 / 99 | 99 / 99 | 15463d8 |
| qwen3.5:4b | 1 | off | 30 / 44 | 0 / 10 | 7 / 42 | 3 / 52 | 66 / 91 | 78 / 91 | 15463d8 |
| qwen3.5:2b | 1 | off | 29 / 44 | 0 / 10 | 7 / 42 | 0 / 52 | 1 / 69 | 63 / 69 | 15463d8 |
| qwen3.5:0.8b | 1 | off | 18 / 44 | 4 / 10 | 15 / 42 | 2 / 52 | 19 / 59 | 21 / 59 | 15463d8 |
| ministral-3:8b | 1 | off | 31 / 44 | 5 / 10 | 15 / 42 | 0 / 52 | 33 / 93 | 71 / 93 | 15463d8 |
| olmo-3:7b-instruct | 1 | off | 20 / 44 | 2 / 10 | 13 / 42 | 0 / 52 | 39 / 78 | 62 / 78 | 15463d8 |
| floor | - | - | 21 / 44 | 0 / 10 | 0 / 42 | 0 / 52 | 0 / 0 | 0 / 0 | 6b75109 |

- **Agreement** is whether the verdict means the same as the gold verdict, decided by Claude Sonnet 5.5 as judge. The judge was checked against hand grades before its scores were counted, and matched twelve of twelve graded blind. With 44 judged items, one item is about 2.3 points.
- **The flag** is read as two rates, never one count: a system that never flags would score well on a count, since settled items outnumber the rest.
- **Cites** are checked against the corpus as written and once a leading `## ` marker, the commonest slip, is removed.
- **The floor** answers "no" to every item, never flags and cites nothing, judged like any other row, so the bottom of the table is measured. It agrees on 21 of 44, and two models score below it.
- **Local models** run through Ollama as their default tags ship them, `Q4_K_M` except `qwen3.5:2b` and `qwen3.5:0.8b` at `Q8_0`, with thinking off and temperature 0. **Opus 5.5** is the ceiling, through the API at effort `high`; it cannot turn thinking off.
- **Answer runs do not reproduce.** Rerun on the same prompts in the same session, `qwen3.5:9b` shared 6 to 11 of 52 replies with its first draw at every stage but level 3, which matched in all three draws. Its agreement across draws: level 1 32 and 34, rerank 35 and 32, lookup 36, 32 and 32, level 3 33 three times, the loop 31 and 30. No 9b stage separates from level 1, and its rows above, the first draw, are not ranked against each other. The other local models were run once, their spread unmeasured.
- **Opus's loop gains five items against level 1 and loses none**, alongside the largest retrieval gain: `invisible-vs-invisible`, `ranged-prone-five-feet`, `readied-attack-extra-attack`, `halfling-greatsword` and `grappler-pin-attacks`. Level 3 gains two and loses none, the lookup gains one, and rerank loses one. Each is one draw. The loop flags 3 of the 10 ambiguous items to level 1's 5, and one settled item.
- **The loop's cost**, per item before the answer call: Opus makes 4.52 calls over 3.15 turns, 7,555 input and 842 output tokens, in 12.9 seconds, and 11 of 52 items reach the six-call cap; `qwen3.5:9b` makes 2.62 calls, 2,478 and 408 tokens, in 5.0 seconds, none capped.

Every number is computed from run records by `scripts/evals/summarize_runs.py --table` and `--gains`, `scripts/evals/score_handed.py` and `scripts/evals/eval_agentic.py --records`. The runs are at commit `15463d8`, the floor at `6b75109` and the 9b's reruns at `fcd6d77`; nothing between them changes how an answer is made. The records are in `results/`: `results/test/` holds the test run and the floor, `results/reruns/` the 9b's reruns, and `results/judge-check/` the run the judge was checked against, with its judged file, recorded on a dirty tree at `66a051b`.

## Reproducing the results

The gold set is `gold/gold.json`, each item a question, its expected verdict, whether it is settled or ambiguous, and the entries its ruling cites, split into dev and test. Tuning happens on dev; test is scored once. The scripts that run a split take `--split test` for the test split and run dev without it. Those that write records write them to `runs/`, which git ignores, each record carrying the commit it ran at and whether the tree was dirty. The records behind the published numbers are in `results/`, so a new run never lands beside them.

| Script | What it does |
|---|---|
| `scripts/evals/eval_retrieval.py` | Scores level 1's retrieval: recall@k and all-cites@k |
| `scripts/evals/eval_multihop.py <model>` | Plans with the model named and scores level 3's fused retrieval |
| `scripts/evals/eval_rerank.py` | Reranks level 1's top 30 with `BAAI/bge-reranker-v2-m3` and scores level 1's order, the reranked order and the two fused |
| `scripts/evals/eval_lookup.py [--kinds <root> ...]` | Links the records each question names ahead of level 1's order and scores both orders, with each kind's link precision and recall |
| `scripts/evals/eval_agentic.py <model> [--records runs/<agentic>.jsonl]` | Runs the loop on every item of the split and scores the ten it hands over, with its calls, turns, tokens and seconds; `--records` prints the same from records already written |
| `scripts/evals/answer_dev.py <model> [--level 1\|3] [--rerank\|--lookup\|--loop-records runs/<agentic>.jsonl]` | Rules on every item of the split; a model named `claude-…` answers through the API; `--rerank` answers level 1 from its order fused with the reranked one; `--lookup` answers from the records the question names ahead of level 1's order; `--loop-records` answers from the ten each loop record handed over |
| `scripts/evals/judge_dev.py runs/<run>.jsonl` | Judges a run's verdicts and flags with Claude Sonnet 5.5 |
| `scripts/evals/floor_dev.py` | Writes the floor row: "no" to every item, no flag, no cites |
| `scripts/evals/summarize_runs.py --table runs/<run>.jsonl ...` | Prints the results table from judged runs; `--gains <base> <stage>` names the items each of two runs agreed on and the other did not |
| `scripts/evals/score_handed.py runs/<run>.jsonl ...` | Scores the ten each answer run retrieved, recall@k and all-cites@k against the gold cites, and refuses a run recorded on a dirty tree |
| `scripts/evals/rescore_test.py [--dry-run]` | Reruns every published row on test at one clean commit, judges each and prints the tables, stopping on the first failure; `--dry-run` prints the commands |
| `scripts/evals/check_gate.py <model>` | Runs the gate over the gold questions and `gold/gate-refusals.json`, a set it must refuse |
| `scripts/app/check_stream.py <id> ...` | Posts gold items to the running server and checks each matches its measured record |
| `scripts/corpus/check_supplement.py <srd.txt>` | Checks every passage in `supplement.json` word for word against the SRD 5.1 document's text |

The judge and the hosted rows call the Claude API and authenticate with the profile `ant auth login` stores; a set `ANTHROPIC_API_KEY` takes precedence over it, even an empty one. Everything else runs locally. `scripts/corpus/pull_srd.py` refetches the corpus at its pinned commit.

The rerank scripts need the `rerank` extra, sentence-transformers on PyTorch, which the screen does not use. On Windows, PyPI's torch is CPU-only, so it comes from PyTorch's CUDA 13.2 index:

```
.venv/Scripts/python -m pip install -e ".[dev,rerank]" --extra-index-url https://download.pytorch.org/whl/cu132
```

## Measuring your own model

A model pulled into Ollama is measured on the test split, the split the published rows are scored on, so its row sits beside theirs. Dev is where a choice is tuned before test is run. Every step but the judge runs locally. Each record carries the commit it ran at, so commit any change first: `score_handed.py` refuses a run recorded on a dirty tree.

**1. The key-order check.** The ruling's fields are ordered so the model reasons and flags before it rules, and some models' templates make Ollama sort a schema's keys. A model that fails this check rules before it reasons, and its row would not measure the same thing:

```
.venv/Scripts/python scripts/evals/check_key_order.py <model>
```

The model runs with its template and penalties as shipped, and no row gets a prompt of its own.

**2. The answers.** One record per test item, written to `runs/<stamp>-test-<model>.jsonl`, any `:` in the model's name written as `-`. `--level 3` has the model plan sub-questions first and writes `runs/<stamp>-test-level3-<model>.jsonl`:

```
.venv/Scripts/python scripts/evals/answer_dev.py <model> --split test
```

**3. Retrieval.** recall@k and all-cites@k on the ten entries the model was handed, read beside the Retrieval table above:

```
.venv/Scripts/python scripts/evals/score_handed.py runs/<run>.jsonl
```

At level 1 these are the embedder's, the same for every answering model; at level 3 they are the model's plans, which change from draw to draw. This is as far as the measurement goes without a Claude account. To compare an embedder instead, add it to `EMBEDDERS` in `src/rules_attorney/retrieve.py` and run `scripts/evals/eval_retrieval.py`.

**4. The judge.** Claude Sonnet 5.5 decides each verdict's agreement and writes `runs/<run>.judged-claude-sonnet-5-5.jsonl` beside the run. It needs a Claude account, authenticated as above:

```
.venv/Scripts/python scripts/evals/judge_dev.py runs/<run>.jsonl
```

**5. The table.** Your row, with any published run after it for comparison, here `qwen3.5:9b` at level 1:

```
.venv/Scripts/python scripts/evals/summarize_runs.py --table runs/<run>.jsonl results/test/20261105-151232-test-qwen3.5-9b.jsonl
```

An answer run is one draw. Rerun on the same prompts, `qwen3.5:9b`'s agreement moved by up to four items, and one item of 44 is about 2.3 points, so a gap of one item between rows is not a finding.

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