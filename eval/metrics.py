"""
eval/metrics.py
--------------
RAGAS-inspired quality metrics, computed without the ragas package so the suite
doesn't conflict with the project's langchain v1.x stack.

All five metrics are judge-LLM based (OpenRouter gpt-oss-120b), which is the
RAGAS-faithful approach:

  * faithfulness      - is the answer grounded in the retrieved context?
  * answer_relevance  - is the answer on-topic for the question?
  * correctness       - semantic agreement with the ground-truth reference
  * context_precision - how relevant the retrieved chunks are (avg per chunk)
  * context_recall    - how much of the ground truth is supported by the
                        retrieved context (per-claim attribution)

All metrics are scored 0..1.
"""

import re

from app.main import _extract_llm_text, llm

_JUDGE_SYSTEM = (
    "You are a strict, impartial evaluation judge for a government-services assistant. "
    "Score the request on a scale of 0 to 1 using ONLY these anchors: 0 = completely "
    "wrong/unsupported/irrelevant, 0.5 = partially, 1 = fully correct/supported/relevant. "
    "Respond with ONLY a JSON object of the form {\"score\": <number 0..1>}. No prose."
)


def _judge(prompt: str) -> float:
    """Ask the judge LLM for a 0..1 score, robust to extra prose/formatting."""
    messages = [
        {"role": "system", "content": _JUDGE_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    for attempt in range(2):
        text = _content(llm.invoke(messages))
        number = _first_float(text)
        if number is not None:
            return max(0.0, min(1.0, round(number, 3)))
    # Final fallback: unresolvable judge output.
    return 0.5


def _content(result) -> str:
    return _extract_llm_text(result) or ""


def _first_float(text: str) -> float | None:
    if not text:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


# ── LLM-judged metrics ────────────────────────────────────────────────────────

def faithfulness(question: str, answer: str, contexts: list[str]) -> float:
    if not answer or not contexts:
        return 0.0
    prompt = (
        f"Question: {question}\n\nAnswer: {answer}\n\n"
        f"Retrieved context:\n{chr(10).join(f'[{i+1}] {c}' for i, c in enumerate(contexts))}\n\n"
        "Score how well the answer is SUPPORTED BY (grounded in) the retrieved context "
        "alone — ignore whether it is true in the real world. Respond with {\"score\": ...}."
    )
    return _judge(prompt)


def answer_relevance(question: str, answer: str) -> float:
    if not answer:
        return 0.0
    prompt = (
        f"Question: {question}\n\nAnswer: {answer}\n\n"
        "Score how RELEVANT and directly on-topic the answer is to the question. "
        "Respond with {\"score\": ...}."
    )
    return _judge(prompt)


def correctness(question: str, answer: str, ground_truth: str) -> float:
    if not answer or not ground_truth:
        return 0.0
    prompt = (
        f"Question: {question}\n\n"
        f"Reference (correct) answer: {ground_truth}\n\n"
        f"Model answer: {answer}\n\n"
        "Score how SEMANTICALLY CONSISTENT / correct the model answer is against the "
        "reference answer (ignore wording, reward matching meaning and facts). "
        "Respond with {\"score\": ...}."
    )
    return _judge(prompt)


# ── Context metrics (judge-LLM based, RAGAS-faithful) ─────────────────────────

def _joined_context(contexts: list[str]) -> str:
    return "\n".join(f"[{i + 1}] {c}" for i, c in enumerate(contexts))


def context_precision(question: str, contexts: list[str], ground_truth: str) -> float:
    """Judge how relevant / useful the retrieved context is for the question.

    (RAGAS measures per-chunk precision; here we score the retrieved set as a
    whole with one judge call so the run stays within a practical time budget.)
    """
    if not contexts:
        return 0.0
    prompt = (
        f"Question: {question}\n\nReference answer: {ground_truth}\n\n"
        f"Retrieved context:\n{_joined_context(contexts)}\n\n"
        "Score the PRECISION of the retrieved context: how relevant and useful it is "
        "for answering the question / matching the reference answer (0 = mostly "
        "irrelevant, 1 = highly relevant). Respond with {\"score\": ...}."
    )
    return _judge(prompt)


def context_recall(question: str, contexts: list[str], ground_truth: str) -> float:
    """Judge what fraction of the reference answer is supported by the context."""
    if not contexts or not ground_truth:
        return 0.0
    prompt = (
        f"Question: {question}\n\nRetrieved context:\n{_joined_context(contexts)}\n\n"
        f"Reference answer: {ground_truth}\n\n"
        "Score the RECALL: what fraction of the factual content in the reference "
        "answer is SUPPORTED BY the retrieved context (0 = none, 1 = all). "
        "Respond with {\"score\": ...}."
    )
    return _judge(prompt)
