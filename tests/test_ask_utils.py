"""
Unit tests for the /ask helpers in app/ask_utils.py:
  * SYSTEM_PROMPTS (English + Nepali, JSON shape)
  * parse_ask_json (valid / fenced / malformed / non-dict / unknown topic)
  * build_ask_response (guide_link + guide_service_id logic)
  * resolve_guide_service (topic → real gov_services row)
"""

import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ask_utils import (
    SYSTEM_PROMPTS,
    GUIDE_ROUTES,
    build_ask_response,
    parse_ask_json,
    resolve_guide_service,
)
from app.models import Base, GovService


# ── SYSTEM PROMPTS ────────────────────────────────────────────────────────────

def test_system_prompts_have_both_variants():
    assert "ENGLISH" in SYSTEM_PROMPTS
    assert "NEPALI" in SYSTEM_PROMPTS
    assert "{context}" in SYSTEM_PROMPTS["ENGLISH"]
    assert "{question}" in SYSTEM_PROMPTS["ENGLISH"]
    assert "{context}" in SYSTEM_PROMPTS["NEPALI"]
    assert "{question}" in SYSTEM_PROMPTS["NEPALI"]


def test_nepali_prompt_keeps_json_keys_english():
    ne = SYSTEM_PROMPTS["NEPALI"]
    # The JSON keys are parsed by code and must stay English in both variants.
    assert '"topic":' in ne
    assert '"suggest_guide":' in ne
    assert '"answer":' in ne


# ── PARSE ─────────────────────────────────────────────────────────────────────

def test_parse_valid_json():
    parsed = parse_ask_json(
        '{"answer": "Visit a NID enrollment center with your citizenship.", '
        '"topic": "nid", "suggest_guide": true}'
    )
    assert parsed["answer"].startswith("Visit a NID")
    assert parsed["topic"] == "nid"
    assert parsed["suggest_guide"] is True


def test_parse_code_fenced_json():
    parsed = parse_ask_json(
        '```json\n{"answer": "Short answer", "topic": "passport", "suggest_guide": true}\n```'
    )
    assert parsed["answer"] == "Short answer"
    assert parsed["topic"] == "passport"
    assert parsed["suggest_guide"] is True


def test_parse_malformed_json_falls_back_to_raw_text():
    raw = "Here is a plain-text answer, no JSON at all."
    parsed = parse_ask_json(raw)
    assert parsed["answer"] == raw
    assert parsed["topic"] is None
    assert parsed["suggest_guide"] is False


def test_parse_non_dict_json_falls_back():
    parsed = parse_ask_json('["just", "a", "list"]')
    assert parsed["topic"] is None
    assert parsed["suggest_guide"] is False
    assert parsed["answer"] == '["just", "a", "list"]'


def test_parse_unknown_topic_is_nulled():
    parsed = parse_ask_json(
        '{"answer": "Hi", "topic": "tax_return", "suggest_guide": true}'
    )
    assert parsed["topic"] is None
    assert parsed["suggest_guide"] is True  # bool survives


# ── BUILD RESPONSE ────────────────────────────────────────────────────────────

def test_build_response_with_topic_and_guide():
    resp = build_ask_response(
        {"answer": "Short", "topic": "nid", "suggest_guide": True},
        ["file.pdf"],
        guide_service_id=2,
    )
    assert resp["guide_link"] == GUIDE_ROUTES["nid"]
    assert resp["guide_service_id"] == 2
    assert resp["sources"] == ["file.pdf"]


def test_build_response_suggest_false_omits_guide():
    resp = build_ask_response(
        {"answer": "Short", "topic": "nid", "suggest_guide": False},
        [],
        guide_service_id=2,
    )
    assert resp["guide_link"] is None
    assert resp["guide_service_id"] is None


def test_build_response_null_topic_omits_guide():
    resp = build_ask_response(
        {"answer": "Short", "topic": None, "suggest_guide": True},
        [],
        guide_service_id=None,
    )
    assert resp["guide_link"] is None
    assert resp["guide_service_id"] is None


# ── RESOLVE GUIDE SERVICE ─────────────────────────────────────────────────────

@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    # Mirrors the real seed: active services are not sequential (DL is id 7).
    with testing_session() as db:
        rows = [
            ("Citizenship Certificate Copy", True),
            ("NID Registration", True),
            ("E-Passport Apply", True),
            ("Bluebook Renewal", False),
            ("Driving License", True),
        ]
        for title, active in rows:
            db.add(GovService(title=title, category="Test", is_active=active))
        db.commit()
        yield testing_session
    Base.metadata.drop_all(bind=engine)


def test_resolve_guide_service_returns_correct_rows(db_session):
    with db_session() as db:
        assert resolve_guide_service(db, "citizenship").title == "Citizenship Certificate Copy"
        assert resolve_guide_service(db, "nid").title == "NID Registration"
        assert resolve_guide_service(db, "passport").title == "E-Passport Apply"
        # Driving License is id 7 in the real DB — resolving by title, not id.
        assert resolve_guide_service(db, "driving_license").title == "Driving License"


def test_resolve_guide_service_unknown_topic(db_session):
    with db_session() as db:
        assert resolve_guide_service(db, "tax_return") is None
        assert resolve_guide_service(db, None) is None
