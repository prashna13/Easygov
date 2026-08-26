"""
eval/pipeline.py
----------------
In-process retrieval + answer generation mirroring the production /ask endpoint,
so the evaluation drives the exact same code path (vector store, prompt, LLM,
JSON parsing) without needing a running server.

Run in NON-lite mode so the real embedding model, Chroma store and LLM load.
"""

import os
import sys

# Ensure the project root is importable.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Guarantee the heavy stack is loaded (never run eval in lite mode).
os.environ.pop("EASYGOV_LITE", None)

from langdetect import detect, LangDetectException  # noqa: E402

from app.ask_utils import SYSTEM_PROMPTS, parse_ask_json  # noqa: E402
from app.main import (  # noqa: E402
    _extract_llm_text,
    llm,
    retriever_k,
    vector_db,
)


def retrieve_contexts(question: str, k: int | None = None) -> list[str]:
    """Return the top-k retrieved chunk texts for a question."""
    k = k or retriever_k
    docs = vector_db.similarity_search(question, k=k)
    return [getattr(d, "page_content", "") or "" for d in docs]


def _detect_lang(question: str) -> str:
    """Mirror /ask: Nepali questions get the Nepali prompt, else English."""
    try:
        query_lang = detect(question)
    except LangDetectException:
        query_lang = "en"
    return "NEPALI" if query_lang == "ne" else "ENGLISH"


def generate_answer(question: str, k: int | None = None) -> dict:
    """Produce {answer, contexts} exactly as /ask would."""
    contexts = retrieve_contexts(question, k=k)
    prompt_lang = _detect_lang(question)

    context = "\n\n".join(ctx for ctx in contexts if ctx)
    prompt = (
        SYSTEM_PROMPTS[prompt_lang]
        .replace("{context}", context)
        .replace("{question}", question)
    )

    result = llm.invoke(prompt)
    raw = _extract_llm_text(result)
    parsed = parse_ask_json(raw)
    answer = (parsed.get("answer") or raw).strip()

    return {"answer": answer, "contexts": contexts}
