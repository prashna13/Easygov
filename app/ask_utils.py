"""
ask_utils.py
------------
Pure helpers for the RAG chatbot endpoint (POST /ask).

Kept in a lightweight module (no FastAPI app, no embedding model) so it can be
unit-tested in isolation. Holds:

  * SYSTEM_PROMPTS   — the concise-answer system prompts (English + Nepali)
  * GUIDE_ROUTES     — topic → guide route mapping
  * parse_ask_json   — tolerant parser for the LLM's JSON reply
  * build_ask_response — assembles the API response (answer + guide deep-link)
  * resolve_guide_service — maps a topic to the real gov_services row
"""

import json
import re
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import GovService as DBGovService

# Topic → fixed guide route (used to deep-link into the app's guide screens).
GUIDE_ROUTES = {
    "citizenship": "/guides/citizenship",
    "nid": "/guides/nid",
    "passport": "/guides/passport",
    "driving_license": "/guides/driving-license",
}

# Topic → English title of the service row in gov_services (seed data).
GUIDE_SERVICE_TITLES = {
    "citizenship": "Citizenship Certificate Copy",
    "nid": "NID Registration",
    "passport": "E-Passport Apply",
    "driving_license": "Driving License",
}

_INSTRUCTIONS_EN = (
    "You are EasyGov's assistant, helping Nepali citizens navigate government services.\n"
    "Answer the user's question directly in 2-4 short sentences. Do not enumerate the full "
    "step-by-step procedure, full document checklist, or full fee table unless the user "
    'explicitly asks for "all the steps," "the full process," or similar. The user always has '
    "access to a complete, detailed guide elsewhere in the app for citizenship, NID, passport, "
    "and driving license \u2014 your job is to give a quick, useful answer and point them to that "
    "guide for full depth, not to reproduce it.\n"
    "If the retrieved context contains a long procedure, summarize only the part most directly "
    "relevant to their specific question.\n"
    'Respond ONLY in this exact JSON shape, with no text outside the JSON:\n'
    '{"answer": "<your short answer>", "topic": "citizenship" | "nid" | "passport" | "driving_license" | null, "suggest_guide": true | false}\n'
    'Set "topic" to whichever of the four services the question is about, or null if none apply.\n'
    'Set "suggest_guide" to true whenever the question concerns a procedure, requirement, '
    "document, fee, or step \u2014 i.e. whenever pointing the user to the full guide would help.\n\n"
    "GROUNDING & SCOPE RULES (most important):\n"
    "Answer ONLY from the provided CONTEXT. Do not use general knowledge; never invent "
    "dates, fees, steps, procedures or details that are not in the CONTEXT.\n"
    "If the provided CONTEXT is IRRELEVANT to the question, or does not contain enough "
    "information to answer it, reply with a short, polite message that you can only help "
    "with the government services available in the app, and set \"topic\": null and "
    "\"suggest_guide\": false. Do not answer from general knowledge.\n"
    "Do NOT refuse a question just because the topic is not on a fixed list of services — "
    "the CONTEXT is the source of truth: if it contains a relevant answer, answer from it.\n\n"
    "CONTEXT (might be in Nepali or English):\n{context}\n\n"
    "QUESTION:\n{question}\n"
    "ANSWER IN ENGLISH."
)

_INSTRUCTIONS_NE = (
    "\u0924\u092a\u093e\u0908\u0902 EasyGov \u0915\u094b \u0938\u0939\u093e\u092f\u0915 \u0939\u0941\u0928\u0941\u0939\u0941\u0928\u094d\u091b, \u0928\u0947\u092a\u093e\u0932\u0940 \u0928\u093e\u0917\u0930\u093f\u0915\u0939\u0930\u0942\u0932\u093e\u0908 \u0938\u0930\u0915\u093e\u0930\u0940 \u0938\u0947\u0935\u093e\u0939\u0930\u0942 \u0928\u0947\u092d\u093f\u0917\u0947\u091f \u0917\u0930\u094d\u0928 \u092e\u0926\u094d\u0926\u0924 \u0917\u0930\u094d\u0928\u0947\u0964\n"
    "\u092a\u094d\u0930\u092f\u094b\u0917\u0915\u0930\u094d\u0924\u093e\u0915\u094b \u092a\u094d\u0930\u0936\u094d\u0928\u0915\u094b \u0938\u0940\u0927\u093e \u0930\u0942\u092a\u092e\u093e 2\u20134 \u091b\u094b\u091f\u093e \u0935\u093e\u0915\u094d\u092f\u092e\u093e \u091c\u0935\u093e\u092b \u0926\u093f\u0928\u0941\u0939\u094b\u0938\u094d\u0924\u0964 \u091a\u0930\u0923-\u0926\u0930-\u091a\u0930\u0923 \u092a\u0942\u0930\u093e \u092a\u094d\u0930\u0915\u094d\u0930\u093f\u092f\u093e, \u092a\u0942\u0930\u093e \u0915\u093e\u0917\u091c\u093e\u0924 \u091a\u0947\u0915\u0932\u093f\u0938\u094d\u091f, \u0935\u093e \u092a\u0942\u0930\u093e \u0936\u0941\u0932\u094d\u0915 \u0924\u093e\u0932\u093f\u0915\u093e \u0938\u0942\u091a\u0940\u092c\u0926\u094d\u0927 \u0928\u0917\u0930\u094d\u0928\u0941\u0939\u094b\u0938\u094d\u0924 \u2014 \u091c\u092c\u0938\u092e\u094d\u092e \u092a\u094d\u0930\u092f\u094b\u0917\u0915\u0930\u094d\u0924\u093e\u0932\u0947 \u0938\u094d\u092a\u0937\u094d\u091f \u0930\u0942\u092a\u092e\u093e \u201c\u0938\u092c\u0948 \u091a\u0930\u0923\u0939\u0930\u0942,\u201d \u201c\u092a\u0942\u0930\u093e \u092a\u094d\u0930\u0915\u094d\u0930\u093f\u092f\u093e,\u201d \u0935\u093e \u0938\u094b\u091c\u0948 \u0938\u094b\u0927\u0947\u0915\u093e \u091b\u0948\u0928\u0928\u094d\u0964 \u092a\u094d\u0930\u092f\u094b\u0917\u0915\u0930\u094d\u0924\u093e\u0915\u0939\u093e\u0901 \u0928\u093e\u0917\u0930\u093f\u0915\u0924\u093e, NID, \u092a\u093e\u0938\u092a\u094b\u0930\u094d\u091f, \u0930 \u0921\u094d\u0930\u093e\u0907\u092d\u093f\u0919 \u0932\u093e\u0907\u0938\u0947\u0928\u094d\u0938\u0915\u093e \u0932\u093e\u0917\u093f \u090f\u092a\u092e\u093e \u092a\u0942\u0930\u094d\u0923 \u0935\u093f\u0938\u094d\u0924\u0943\u0924 \u0917\u093e\u0907\u0921 \u0938\u0927\u0948\u0902 \u0909\u092a\u0932\u092c\u094d\u0927 \u091b \u2014 \u0924\u092a\u093e\u0908\u0902\u0915\u094b \u0915\u093e\u092e \u091b\u093f\u091f\u094b, \u0909\u092a\u092f\u094b\u0917\u0940 \u091c\u0935\u093e\u092b \u0926\u093f\u0928\u0941 \u0930 \u092a\u0942\u0930\u093e \u0935\u093f\u0935\u0930\u0923\u0915\u093e \u0932\u093e\u0917\u093f \u0924\u094d\u092f\u094b \u0917\u093e\u0907\u0921\u0924\u0930\u094d\u092b \u092a\u0920\u093e\u0909\u0928\u0941 \u0939\u094b, \u0924\u094d\u092f\u0938\u094d\u0915\u094b \u092a\u0941\u0928: \u0909\u0924\u094d\u092a\u093e\u0926\u0928 \u0917\u0930\u094d\u0928\u0941 \u0939\u094b\u0908\u0928\u0964\n"
    "\u092f\u0926\u093f \u092a\u094d\u0930\u093e\u092a\u094d\u0924 \u0938\u0928\u094d\u0926\u0930\u094d\u092d\u092e\u093e \u0932\u093e\u092e\u094b \u092a\u094d\u0930\u0915\u094d\u0930\u093f\u092f\u093e \u091b \u092d\u0928\u0947, \u092a\u094d\u0930\u092f\u094b\u0917\u0915\u0930\u094d\u0924\u093e\u0915\u094b \u0935\u093f\u0936\u0947\u0937 \u092a\u094d\u0930\u0936\u094d\u0928\u0938\u0901\u0917 \u0938\u092c\u0948\u092d\u0928\u094d\u0926\u093e \u0938\u0940\u0927\u093e \u0938\u092e\u094d\u092c\u0928\u094d\u0927\u093f\u0924 \u092d\u093e\u0917 \u092e\u093e\u0924\u094d\u0930 \u0938\u093e\u0930\u093e\u0902\u0936\u093f\u0924 \u0917\u0930\u094d\u0928\u0941\u0939\u094b\u0938\u094d\u0924\u0964\n"
    '\u0935\u093f\u0936\u0947\u0937\u0924\u0903 \u092f\u094b \u0920\u093f\u0915 JSON \u0922\u093e\u0901\u091a\u093e\u092e\u093e \u092e\u093e\u0924\u094d\u0930 \u091c\u0935\u093e\u092b \u0926\u093f\u0928\u0941\u0939\u094b\u0938\u094d\u0924, JSON \u092c\u093e\u0939\u093f\u0930 \u0915\u0941\u0928\u0948 \u092a\u093e\u0920 \u0928\u0930\u093e\u0916\u0940:\n'
    '{"answer": "<\u0924\u092a\u093e\u0908\u0902\u0915\u094b \u091b\u094b\u091f\u094b \u091c\u0935\u093e\u092b>", "topic": "citizenship" | "nid" | "passport" | "driving_license" | null, "suggest_guide": true | false}\n'
    '"topic" \u092a\u094d\u0930\u0936\u094d\u0928 \u0915\u0941\u0928 \u091a\u093e\u0930 \u0938\u0947\u0935\u093e\u092e\u0927\u094d\u092f\u0947 \u090f\u0901\u091f\u093e\u0938\u0901\u0917 \u0938\u092e\u094d\u092c\u0928\u094d\u0927\u093f\u0924 \u091b \u092d\u0928\u0947 \u0924\u094d\u092f\u094b \u092e\u093e\u0928\u092e\u093e \u0938\u0947\u091f \u0917\u0930\u094d\u0928\u0941\u0939\u094b\u0938\u094d\u0924, \u0915\u0941\u0928\u0948 \u092a\u0928\u093f \u0932\u093e\u0917\u0942 \u0928\u092d\u090f null \u0930\u093e\u0916\u094d\u0928\u0941\u0939\u094b\u0938\u094d\u0924\u0964 topic \u092e\u093e\u0928\u0939\u0930\u0942 \u0938\u0927\u0948\u0902 \u0905\u0902\u0917\u094d\u0930\u0947\u091c\u0940\u092e\u093e \u0930\u093e\u0916\u094d\u0928\u0941\u0939\u094b\u0938\u094d\u0924\u0964\n'
    '"answer" \u0930 "suggest_guide" \u0915\u0941\u091e\u094d\u091c\u0940\u0939\u0930\u0942 \u0905\u0902\u0917\u094d\u0930\u0947\u091c\u0940\u092e\u0948 \u0930\u093e\u0916\u094d\u0928\u0941\u0939\u094b\u0938\u094d\u0924 \u2014 \u0915\u0947\u0935\u0932 "answer" \u0915\u094b \u0938\u093e\u092e\u0917\u094d\u0930\u0940 \u0930 \u0928\u093f\u0930\u094d\u0926\u0947\u0936\u0928\u0939\u0930\u0942 \u0928\u0947\u092a\u093e\u0932\u0940\u092e\u093e\u0964\n'
    '"suggest_guide" \u092a\u094d\u0930\u0936\u094d\u0928 \u092a\u094d\u0930\u0915\u094d\u0930\u093f\u092f\u093e, \u0906\u0935\u0936\u094d\u092f\u0915\u0924\u093e, \u0915\u093e\u0917\u091c\u093e\u0924, \u0936\u0941\u0932\u094d\u0915, \u0935\u093e \u091a\u0930\u0923\u0938\u0901\u0917 \u0938\u092e\u094d\u092c\u0928\u094d\u0927\u093f\u0924 \u092d\u090f \u2014 \u0905\u0930\u094d\u0925\u093e\u0924\u094d \u092a\u094d\u0930\u092f\u094b\u0917\u0915\u0930\u094d\u0924\u093e\u0932\u093e\u0908 \u092a\u0942\u0930\u093e \u0917\u093e\u0907\u0921\u0924\u0930\u094d\u092b \u092a\u0920\u093e\u0909\u0928\u0941 \u0938\u0939\u092f\u094b\u0917\u0940 \u0939\u0941\u0928\u0947 \u0939\u0930\u0947\u0915 \u0905\u0935\u0938\u094d\u0925\u093e\u092e\u093e true \u0938\u0947\u091f \u0917\u0930\u094d\u0928\u0941\u0939\u094b\u0938\u094d\u0924\u0964\n\n'
    "सबैभन्दा महत्त्वपूर्ण — नियमहरू:\n"
    "जवाफ केवल दिइएको CONTEXT बाट मात्र दिनुहोस्। सामान्य ज्ञान प्रयोग नगर्नुहोस्; CONTEXT मा नभएको मिति, शुल्क, चरण वा विवरण कहिल्यै नबनाउनुहोस्।\n"
    "यदि दिइएको CONTEXT प्रश्नसँग असम्बन्धित छ, वा जवाफ दिन पर्याप्त जानकारी छैन भने, तपाईं एपमा उपलब्ध सरकारी सेवाहरूमा मात्र सहयोग गर्न सक्नुहुन्छ भनी छोटो, विनम्र सन्देश दिनुहोस्, र \"topic\": null र \"suggest_guide\": false सेट गर्नुहोस्। सामान्य ज्ञानबाट जवाफ नदिनुहोस्।\n"
    "कुनै निश्चित सेवा सूचीमा नभएकै कारणले प्रश्नलाई अस्वीकार नगर्नुहोस् — CONTEXT नै स्रोत हो: यदि यसमा सान्दर्भिक जवाफ छ भने त्यसबाट जवाफ दिनुहोस्।\n\n"
    "\u0938\u0928\u094d\u0926\u0930\u094d\u092d (\u0928\u0947\u092a\u093e\u0932\u0940 \u0935\u093e \u0905\u0902\u0917\u094d\u0930\u0947\u091c\u0940\u092e\u093e \u0939\u0941\u0928 \u0938\u0915\u094d\u091b):\n{context}\n\n"
    "\u092a\u094d\u0930\u0936\u094d\u0928:\n{question}\n"
    "\u0909\u0924\u094d\u0924\u0930 \u0928\u0947\u092a\u093e\u0932\u0940\u092e\u093e \u0926\u093f\u0928\u0941\u0939\u094b\u0938\u094d\u0924\u0964"
)

# answer_lang key ("ENGLISH" / "NEPALI") → prompt template with {context} and {question}.
SYSTEM_PROMPTS = {
    "ENGLISH": _INSTRUCTIONS_EN,
    "NEPALI": _INSTRUCTIONS_NE,
}


def parse_ask_json(raw_text: str) -> dict:
    """Parse the LLM's JSON reply into {answer, topic, suggest_guide}.

    The model occasionally wraps the JSON in ```json fences or returns plain
    text. Any failure falls back to treating the raw text as the answer with
    topic=None and suggest_guide=False (never errors the request).
    """
    cleaned = (raw_text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("LLM reply is not a JSON object")
        topic = parsed.get("topic")
        topic = topic if isinstance(topic, str) and topic in GUIDE_ROUTES else None
        return {
            "answer": str(parsed.get("answer", "")).strip() or raw_text.strip(),
            "topic": topic,
            "suggest_guide": bool(parsed.get("suggest_guide", False)),
        }
    except Exception:
        return {"answer": raw_text.strip(), "topic": None, "suggest_guide": False}


OFFICIAL_GOV_CITATIONS = {
    "passport": "[Department of Passports](https://nepalpassport.gov.np)",
    "nid": "[DoNIDCR - National ID Portal](https://donidcr.gov.np)",
    "citizenship": "[Ministry of Home Affairs](https://moha.gov.np)",
    "driving_license": "[Department of Transport Management](https://dotm.gov.np)",
    "business_registration": "[Office of Company Registrar](https://ocr.gov.np)",
    "pan": "[Inland Revenue Department](https://ird.gov.np)",
}


def build_ask_response(
    parsed: dict,
    sources: List[str],
    guide_service_id: Optional[int] = None,
) -> dict:
    """Assemble the /ask response: concise answer + single official government site citation + optional guide deep-link."""
    topic = parsed.get("topic")
    suggest_guide = parsed.get("suggest_guide", False)

    single_source = None

    if topic and topic in OFFICIAL_GOV_CITATIONS:
        single_source = OFFICIAL_GOV_CITATIONS[topic]

    if not single_source:
        for src in sources:
            src_lower = src.lower()
            for top, citation in OFFICIAL_GOV_CITATIONS.items():
                top_normalized = top.replace("_", "")
                if top in src_lower or top_normalized in src_lower.replace("_", ""):
                    single_source = citation
                    break
            if single_source:
                break

    if not single_source and sources:
        single_source = sources[0]

    final_sources = [single_source] if single_source else []

    return {
        "answer": parsed.get("answer", ""),
        "sources": final_sources,
        "guide_link": GUIDE_ROUTES.get(topic) if (suggest_guide and topic) else None,
        "guide_service_id": guide_service_id if (suggest_guide and topic) else None,
    }


def resolve_guide_service(db: Session, topic: Optional[str]):
    """Return the gov_services row matching `topic`, or None if unknown."""
    if not topic or topic not in GUIDE_SERVICE_TITLES:
        return None
    return db.query(DBGovService).filter(DBGovService.title == GUIDE_SERVICE_TITLES[topic]).first()
