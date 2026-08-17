# -*- coding: utf-8 -*-
"""
translate_seed.py
-----------------
One-off script that generates Nepali (Devanagari) translations of the EasyGov
seed content using the configured OpenRouter LLM, and writes them to
`app/nepali_content.py`.

Outputs (keys used by seed_data.py and main.py):
  SERVICE_NE             : { service_title: {title, category, description, guidance} }
  STEP_TEMPLATES_NE      : { service_title: [(step_name_ne, step_desc_ne), ...] }
  DEFAULT_STEP_TEMPLATE_NE : [(step_name_ne, step_desc_ne), ...]
  SEED_STEPS_NE          : { "NID_STEPS": [...], "CITIZENSHIP_STEPS": [...] }

Usage (from project root):
    python app/translate_seed.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "nepali_content.py")

# English source content
from app.seed_data import GOV_SERVICES_DATA, NID_STEPS, CITIZENSHIP_STEPS  # noqa: E402
from app.step_templates import STEP_TEMPLATES as STEP_TEMPLATES_EN  # noqa: E402
from app.step_templates import DEFAULT_STEP_TEMPLATE as DEFAULT_STEP_TEMPLATE_EN  # noqa: E402

llm = ChatOpenAI(
    model=os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b"),
    base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0.1,
)

END_MARKER = "\n[END]"


def _call(text: str, instruction: str) -> str:
    """One LLM call returning the translation only (must end with [END])."""
    prompt = (
        "You are a professional Nepali translator for a Nepali government services app. "
        "Translate the following ENGLISH content into accurate, natural NEPALI "
        "(Devanagari script).\n"
        "Rules:\n"
        "- Translate ALL headings and ALL body text faithfully.\n"
        "- Keep every URL, fee amount, number, date and official acronym (NPR, DAO, NID, "
        "NIN, DoTM, DoNIDCR, OTP, FIR, QR, SMS) unchanged where appropriate.\n"
        "- Keep the same structure: blank lines between paragraphs, lines starting with "
        "'- ' stay bullet lists, ALL-CAPS section headings are translated but kept as headings.\n"
        f"- {instruction}\n"
        "- Do NOT add commentary, notes or explanations. Output ONLY the translation.\n"
        "- End your output with the exact final line: [END]\n\n"
        "--- CONTENT TO TRANSLATE ---\n"
        f"{text}\n"
        "--- TRANSLATION ---\n"
    )
    result = llm.invoke(prompt)
    out = getattr(result, "content", None) or str(result)
    out = out.strip()
    if out.endswith(END_MARKER):
        return out[: -len(END_MARKER)].rstrip()
    # Retry once on truncation
    result = llm.invoke(prompt)
    out = getattr(result, "content", None) or str(result)
    out = out.strip()
    if out.endswith(END_MARKER):
        return out[: -len(END_MARKER)].rstrip()
    raise RuntimeError(f"Translation did not end with [END] marker.\nFirst 300 chars:\n{out[:300]}")


def _chunks(text: str, max_chars: int = 1800):
    """Split text into paragraph-bounded chunks of ~max_chars."""
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars and current:
            chunks.append(current.strip())
            current = para
        else:
            current = (current + "\n\n" + para) if current else para
    if current.strip():
        chunks.append(current.strip())
    return chunks


def translate_service(svc: dict) -> dict:
    """Translate title, category, description and guidance for one service."""
    title = svc["title"]
    print(f"  [{title}]")
    title_ne = _call(title, "Translate this as a short service name/title.")
    category_ne = _call(svc["category"], "Translate this as a short category label.")
    desc_ne = _call(svc["description"], "Translate this short description.")
    chunks = _chunks(svc["guidance"] or "")
    guidance_parts = []
    for i, chunk in enumerate(chunks, start=1):
        note = f"This is part {i} of {len(chunks)} — translate only this part."
        guidance_parts.append(_call(chunk, note))
    return {
        "title": title_ne,
        "category": category_ne,
        "description": desc_ne,
        "guidance": "\n\n".join(guidance_parts),
    }


def translate_steps(steps: list) -> list:
    """Translate a list of (name, description) into (name_ne, desc_ne)."""
    out = []
    for name, desc in steps:
        name_ne = _call(name, "Translate this short step label.")
        desc_ne = _call(desc, "Translate this step instruction.")
        out.append([name_ne, desc_ne])
    return out


def main():
    print("=" * 60)
    print("  EasyGov Nepal — Nepali Translation Generator")
    print("=" * 60)

    data = {"services": {}, "step_templates": {}, "default_step_template": [], "seed_steps": {}}

    active = [s for s in GOV_SERVICES_DATA if s.get("is_active", True)]
    print(f"\n[SERVICES] Translating {len(active)} active services...")
    for svc in active:
        data["services"][svc["title"]] = translate_service(svc)

    print("\n[STEPS] Translating step templates...")
    for title, steps in STEP_TEMPLATES_EN.items():
        print(f"  [{title}] ({len(steps)} steps)")
        data["step_templates"][title] = translate_steps(steps)
    data["default_step_template"] = translate_steps(DEFAULT_STEP_TEMPLATE_EN)

    print("\n[SEED STEPS] Translating seeded test-user steps...")
    data["seed_steps"]["NID_STEPS"] = translate_steps(
        [(s["step_name"], s["step_description"] or "") for s in NID_STEPS]
    )
    data["seed_steps"]["CITIZENSHIP_STEPS"] = translate_steps(
        [(s["step_name"], s["step_description"] or "") for s in CITIZENSHIP_STEPS]
    )

    json_blob = json.dumps(data, ensure_ascii=False, indent=2)

    header = (
        "# -*- coding: utf-8 -*-\n"
        '"""\n'
        "nepali_content.py\n"
        "-----------------\n"
        "Auto-generated Nepali translations for EasyGov Nepal seed content.\n"
        "Do NOT edit manually — regenerate with:  python app/translate_seed.py\n"
        '"""\n\n'
        "import json as _json\n\n"
        "_RAW = "
    )
    footer = (
        "\n\n_DATA = _json.loads(_RAW)\n"
        "SERVICE_NE = _DATA['services']\n"
        "STEP_TEMPLATES_NE = _DATA['step_templates']\n"
        "DEFAULT_STEP_TEMPLATE_NE = _DATA['default_step_template']\n"
        "SEED_STEPS_NE = _DATA['seed_steps']\n"
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(header + json.dumps(json_blob, ensure_ascii=False) + footer)

    print(f"\n[OK] Wrote {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
