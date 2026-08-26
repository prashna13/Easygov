"""
eval/run_eval.py
----------------
RAGAS-style chatbot evaluation runner.

For each QA pair in eval/qa_dataset.jsonl it:
  1. retrieves the context (same pipeline as /ask),
  2. generates the answer,
  3. scores it on five metrics (see eval/metrics.py),
  4. aggregates and compares against thresholds,
  5. writes eval/report.json (per-item + averages + pass/fail) and
     eval/baseline.json (locked averages for regression gating).

Usage:
    python eval/run_eval.py                    # full dataset
    python eval/run_eval.py --limit 5          # smoke run (first 5 items)
    python eval/run_eval.py --no-baseline      # don't write/read baseline
    python eval/run_eval.py --k 4              # override retrieval k
Exit code 1 if any metric is below its threshold.
"""

import argparse
import json
import os
import sys

# Ensure the project root is importable.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from metrics import (  # noqa: E402
    answer_relevance,
    context_precision,
    context_recall,
    correctness,
    faithfulness,
)
from pipeline import generate_answer  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA = os.path.join(HERE, "qa_dataset.jsonl")
REPORT_PATH = os.path.join(HERE, "report.json")
BASELINE_PATH = os.path.join(HERE, "baseline.json")

# Minimum acceptable average per metric (documented in TEST_REPORT.md / README).
THRESHOLDS = {
    "faithfulness": 0.80,
    "answer_relevance": 0.70,
    "context_precision": 0.70,
    "context_recall": 0.70,
    "correctness": 0.60,
}

# Acceptable drop vs baseline before a run is considered a regression.
REGRESSION_TOLERANCE = 0.05

METRICS = list(THRESHOLDS.keys())


def _load_data(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    if not rows:
        raise SystemExit(f"No QA rows found in {path}")
    return rows


def _score_item(item: dict, k: int | None) -> dict:
    question = item["question"]
    ground_truth = item["ground_truth"]
    out = generate_answer(question, k=k)
    answer = out["answer"]
    contexts = out["contexts"]
    return {
        "id": item["id"],
        "service": item.get("service", ""),
        "lang": item.get("lang", "en"),
        "question": question,
        "ground_truth": ground_truth,
        "answer": answer,
        "context_count": len(contexts),
        "faithfulness": faithfulness(question, answer, contexts),
        "answer_relevance": answer_relevance(question, answer),
        "context_precision": context_precision(question, contexts, ground_truth),
        "context_recall": context_recall(question, contexts, ground_truth),
        "correctness": correctness(question, answer, ground_truth),
    }


def _averages(items: list[dict]) -> dict:
    return {
        m: round(sum(it[m] for it in items) / len(items), 3)
        for m in METRICS
    }


def _status(avg: dict, baseline: dict | None) -> dict:
    status = {}
    for m in METRICS:
        ok = avg[m] >= THRESHOLDS[m]
        regressed = False
        if baseline and m in baseline:
            regressed = avg[m] < baseline[m] - REGRESSION_TOLERANCE
        status[m] = {"average": avg[m], "threshold": THRESHOLDS[m], "pass": ok, "regressed": regressed}
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description="EasyGov RAG evaluation")
    parser.add_argument("--data", default=DEFAULT_DATA)
    parser.add_argument("--limit", type=int, default=None, help="only evaluate the first N items")
    parser.add_argument("--k", type=int, default=None, help="override retrieval top-k")
    parser.add_argument("--no-baseline", action="store_true", help="ignore and don't write baseline.json")
    args = parser.parse_args()

    rows = _load_data(args.data)
    if args.limit:
        rows = rows[: args.limit]
    print(f"Evaluating {len(rows)} question(s)...")

    items = [_score_item(it, args.k) for it in rows]
    avg = _averages(items)

    baseline = None
    if not args.no_baseline and os.path.exists(BASELINE_PATH):
        with open(BASELINE_PATH, encoding="utf-8") as f:
            baseline = json.load(f)

    status = _status(avg, baseline)
    any_failed = any(not s["pass"] for s in status.values())
    regressions = [m for m, s in status.items() if s["regressed"]]

    report = {
        "config": {"data": args.data, "limit": args.limit, "k": args.k},
        "n_items": len(items),
        "averages": avg,
        "thresholds": THRESHOLDS,
        "status": status,
        "regressions": regressions,
        "items": items,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n=== Averages ===")
    for m in METRICS:
        s = status[m]
        flag = "PASS" if s["pass"] else "FAIL"
        reg = "  REGRESSED" if s["regressed"] else ""
        print(f"  {m:20} {s['average']:.3f}  (threshold {threshold_label(m)})  {flag}{reg}")

    if not args.no_baseline:
        with open(BASELINE_PATH, "w", encoding="utf-8") as f:
            json.dump(avg, f, ensure_ascii=False, indent=2)
        print(f"\nBaseline locked -> {BASELINE_PATH}")

    print(f"\nReport -> {REPORT_PATH}")
    if any_failed:
        print("\nRESULT: FAIL (metrics below threshold)")
        return 1
    if regressions:
        print(f"\nRESULT: REGRESSION vs baseline ({', '.join(regressions)})")
        return 1
    print("\nRESULT: PASS")
    return 0


def threshold_label(m: str) -> str:
    return f"{THRESHOLDS[m]}"


if __name__ == "__main__":
    sys.exit(main())
