# EasyGov Nepal — Chatbot RAG Evaluation

This `eval/` folder contains a **RAGAS-style** evaluation harness for the `/ask`
chatbot. It is a custom implementation (not the `ragas` package) so it does not
conflict with the project's `langchain` v1.x stack, but it computes the same
metric families and uses the same thresholds.

> The dataset here is a **review draft** (31 items). Finalize the questions and
> reference answers before generating the locked baseline.

---

## What is measured

Each QA pair produces the chatbot's answer plus the retrieved context, then is
scored on five metrics (0–1). All five use the **OpenRouter `gpt-oss-120b`** LLM
as a judge (the RAGAS-faithful approach).

| Metric | How it is computed | Minimum threshold |
|---|---|---|
| **Faithfulness** | Judge: is the answer supported *only* by the retrieved context? | ≥ 0.80 |
| **Answer relevance** | Judge: is the answer on-topic for the question? | ≥ 0.70 |
| **Correctness** | Judge: semantic agreement with the reference answer | ≥ 0.60 |
| **Context precision** | Judge: average relevance of the retrieved chunks to the question/reference | ≥ 0.70 |
| **Context recall** | Judge: fraction of ground-truth claims supported by the retrieved context | ≥ 0.70 |

**Regression gate:** a run fails if any metric is below its threshold, **or** drops
more than **0.05** below the locked `baseline.json`.

---

## Files

| File | Purpose |
|---|---|
| `qa_dataset.jsonl` | 31 QA items (`id`, `service`, `lang`, `question`, `ground_truth`) — 23 English + 8 Nepali, covering citizenship, NID, passport, driving licence, business registration, and general |
| `pipeline.py` | In-process retrieval + generation reusing the exact `/ask` code path (same vector store, prompt, LLM, JSON parsing) |
| `metrics.py` | The five metrics (LLM judge + embedder) |
| `run_eval.py` | Runner: scores all items, aggregates, compares to thresholds, writes `report.json` and `baseline.json` |
| `report.json` | Generated — per-item scores + averages + pass/fail |
| `baseline.json` | Generated — locked averages used for regression gating |

---

## How to run

```powershell
# from the project root (needs OPENROUTER_API_KEY set; loads the embedder once)
python eval/run_eval.py                 # full dataset
python eval/run_eval.py --limit 5       # quick subset
python eval/run_eval.py --k 4           # override retrieval top-k
python eval/run_eval.py --no-baseline   # skip baseline compare/write
```

Exit code `0` = PASS, `1` = a metric below threshold or a regression vs baseline.

**Cost/time estimate:** each item costs roughly 1 generation call plus ~10 judge
calls (3 semantic + context precision × k chunks + context recall × ~ground-truth
claims). A full 31-item run is ~350–450 OpenRouter calls (a few dollars) and takes
a few minutes.

---

## Methodology notes (for the dissertation)

- **Same code path as production**: retrieval uses the real Chroma vector store
  (`vector_db.similarity_search`), the answer is generated with the same system
  prompt and JSON parsing used by `/ask` — so the evaluation measures the shipped
  system, not a mock.
- **Language handling**: Nepali questions are routed to the Nepali prompt, exactly
  as `/ask` does (via `langdetect`).
- **Isolation**: evaluation runs **non-lite** (it must load the real embedder and
  LLM). It is a separate, offline script — it never changes app behavior, and the
  backend test suite (`tests/`) still runs in lite mode.
- **Ground truth**: reference answers are curated from the service guidance in
  `app/seed_data.py` and the ingested `data_source/` documents.
- **Reproducibility**: run with a fixed dataset and `--no-baseline` for the first
  full run; then commit `baseline.json` and re-run to detect regressions.
