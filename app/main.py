import sys
import os
import re
import uuid
from datetime import date
from pathlib import Path

from langchain_core.documents import Document

# Ensure project root is in sys.path when script is executed directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, HTTPException, Depends, status, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from langdetect import detect, LangDetectException

# Heavy ML imports are deferred until needed (see the non-lite block below) so the
# backend test suite can run under EASYGOV_LITE=1 without pulling in torch /
# transformers / the embedding model. They are imported only when the app runs
# normally.
if os.getenv("EASYGOV_LITE", "").strip() != "1":
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
    from langchain_openai import ChatOpenAI

from app.database import get_db
from app.models import (
    User,
    GovService as DBGovService,
    UserService as DBUserService,
    Progress as DBProgress,
    PrerequisiteRule,
    ChatMessage,
    Document as DBDocument,
    ServiceStatus,
    StepStatus,
)
from app.schemas import (
    UserRegister, UserLogin, UserOut, TokenResponse,
    DashboardOut, GovServiceOut, ChatHistoryOut, AskResponse,
    OnboardingRequest, OnboardingResponse, ServiceDetailOut,
    ApplicationOut, ProgressStepOut, DocumentOut, DocumentUpdate,
    AdminServiceSummary, AdminServiceUpdate, AdminIngestResult,
)
from app.auth_utils import (
    hash_password, verify_password, create_access_token,
    get_current_user, get_current_user_optional
)
from app.ask_utils import (
    SYSTEM_PROMPTS, parse_ask_json, build_ask_response, resolve_guide_service,
)
from app.doc_crypto import encrypt_bytes, decrypt_bytes
from app.admin_utils import (
    require_admin,
    reindex_service_guidance,
    ingest_uploaded_document,
    list_ingested_documents,
    delete_ingested_document,
)

load_dotenv()

app = FastAPI(title="EasyGov Nepal API")

# Tests set EASYGOV_LITE=1 to skip loading the heavyweight ML stack (embeddings,
# vector store, LLM) so the test suite stays fast and offline. The /ask, admin
# reindex and ingest routes still work normally at runtime (flag off by default);
# they simply are not exercised by the isolated unit/integration suite.
_LITE = os.getenv("EASYGOV_LITE", "").strip() == "1"

embeddings = None
vector_db = None
llm = None

if not _LITE:
    # 1. Setup the Local Embeddings model
    model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embeddings = HuggingFaceEmbeddings(model_name=model_name)

    # 2. Load the existing vector store from disk
    vector_db = Chroma(
        persist_directory="db_storage/chroma_db",
        embedding_function=embeddings,
    )

# 3. Initialize LLM client
openrouter_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b")
openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
print(f"[EasyGov] Using OpenRouter model: {openrouter_model} @ {openrouter_base_url}")

if not _LITE:
    llm = ChatOpenAI(
        model=openrouter_model,
        base_url=openrouter_base_url,
        api_key=openrouter_api_key,
        temperature=0.2,
    )

# 4. Retrieval settings (RAG)
retriever_k = int(os.getenv("RETRIEVER_K", "6"))
# Cross-lingual retrieval is weaker, so Nepali queries retrieve a wider net
# (only affects multilingual chatbot queries — English / other services unchanged).
MULTILINGUAL_RETRIEVER_K = int(os.getenv("RETRIEVER_K_MULTILINGUAL", "12"))


# ── Hybrid retrieval (vector + lexical) ───────────────────────────────────────
# Vector similarity alone can miss short keyword queries (e.g. "NID fee") because
# the relevant chunk (a small "FEES" section) embeds far from the query while the
# broad service overviews dominate. We complement it with a cheap lexical pass that
# also matches each chunk's service tag, so keyword-focused queries surface the
# right chunk. Built lazily on first call; no dependency (no rank_bm25 needed).

_corpus_cache = None
_corpus_size = -1


def clear_corpus_cache():
    """Clear the lexical corpus cache so the next query re-reads from the DB."""
    global _corpus_cache, _corpus_size
    _corpus_cache = None
    _corpus_size = -1


def _get_corpus():
    """Return a lazy list of (doc_id, text, metadata) for every stored chunk.

    Refreshed automatically when the collection grows (e.g. a doc ingested into
    the running process), so lexical search also sees newly added chunks.
    """
    global _corpus_cache, _corpus_size
    data = vector_db.get()
    total = len(data.get("ids") or [])
    if _corpus_cache is None or total != _corpus_size:
        ids = data.get("ids") or []
        docs = data.get("documents") or []
        metas = data.get("metadatas") or []
        _corpus_cache = list(zip(ids, docs, [m or {} for m in metas]))
        _corpus_size = total
    return _corpus_cache


def _lexical_search(query: str, top_k: int):
    """Rank stored chunks by how many query terms appear in their text + service tag."""
    _STOP = {
        "what", "is", "the", "a", "an", "of", "for", "to", "in", "on", "i", "my",
        "how", "do", "does", "much", "many", "and", "or", "can", "need", "answer",
    }
    terms = set(re.findall(r"[a-z0-9\u0900-\u097f]+", query.lower())) - _STOP
    if not terms:
        return []
    scored = []
    for cid, text, meta in _get_corpus():
        haystack = f"{text} {meta.get('service') or ''}".lower()
        score = sum(1 for t in terms if t in haystack)
        if score:
            scored.append((score, text, meta))
    scored.sort(key=lambda x: (-x[0], len(x[1])))
    return scored[:top_k]


def _translate_to_english(text: str) -> str:
    """Translate a (Nepali) user question to English so retrieval matches the
    English knowledge base. The answer is still produced in the original language."""
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source='ne', target='en').translate(text)
        return translated.strip() if translated else text
    except Exception as e:
        print(f"[EasyGov] Translation error: {e}")
        return text


def hybrid_retrieve(query: str, k: int):
    """Combine vector + lexical retrieval into a single ordered context list.

    Lexical matches (keyword-precise, e.g. "fee" chunks) are surfaced first so
    short keyword questions aren't buried under broad service overviews; vector
    results fill the rest.
    """
    lex = _lexical_search(query, k)
    vector_docs = vector_db.similarity_search(query, k=k)

    seen = set()
    result = []
    for _score, text, meta in lex:
        if text in seen:
            continue
        seen.add(text)
        result.append(Document(page_content=text, metadata=meta))
    for d in vector_docs:
        if d.page_content in seen:
            continue
        seen.add(d.page_content)
        result.append(d)
    return result[:k]

# 5. User document storage — path is env-configurable so tests can redirect it
# to a temp dir and never touch the real db_storage/documents folder.
DOC_STORAGE_DIR = Path(os.getenv("EASYGOV_DOC_STORAGE", "db_storage/documents"))
DOC_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# 6. Minimum age (years) required to register — official documents need 16+
MIN_REGISTRATION_AGE = 16

ALLOWED_DOC_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "application/pdf": ".pdf",
}
MAX_DOC_BYTES = 10 * 1024 * 1024  # 10 MB per file


# ── ONBOARDING / DOCUMENT DEPENDENCY PROFILE ────────────────────────────────
# Keys sent by the mobile app map to gov_services.title values.
ONBOARDING_DOCUMENTS = {
    "citizenship":       "Citizenship Certificate Copy",
    "nid":               "NID Registration",
    "passport":          "E-Passport Apply",
    "driving_license":   "Driving License",
}

# Ordered dependency chain used to pick the recommended "next step".
# Citizenship is the root document; NID builds on it; passport and driving
# license come last (per the Nepal Essential Documents Guide).
NEXT_STEP_CHAIN = [
    "Citizenship Certificate Copy",
    "NID Registration",
    "E-Passport Apply",
    "Driving License",
]

# When every document in the chain is complete, fall back to this service.
NEXT_STEP_FALLBACK = "Driving License"

# Bilingual step templates: English from step_templates.py, Nepali from the
# auto-generated nepali_content.py. Used when starting an application.
from app.step_templates import STEP_TEMPLATES as _STEP_TEMPLATES_EN  # noqa: E402
from app.step_templates import DEFAULT_STEP_TEMPLATE as _DEFAULT_STEP_TEMPLATE_EN  # noqa: E402

try:
    from app.nepali_content import STEP_TEMPLATES_NE, DEFAULT_STEP_TEMPLATE_NE  # noqa: E402
except ImportError:
    # nepali_content.py not generated yet — fall back to English only.
    STEP_TEMPLATES_NE = {}
    DEFAULT_STEP_TEMPLATE_NE = []


def get_step_template(title: str) -> dict:
    """Returns {'en': [...], 'ne': [...]} for a service title's progress steps."""
    en = _STEP_TEMPLATES_EN.get(title, _DEFAULT_STEP_TEMPLATE_EN)
    ne = STEP_TEMPLATES_NE.get(title, DEFAULT_STEP_TEMPLATE_NE)
    if len(ne) < len(en):
        ne = ne + [("", "")] * (len(en) - len(ne))
    return {"en": en, "ne": ne[: len(en)]}


def get_completed_service_ids(db: Session, user: User) -> set:
    """Set of service ids the user has fully completed."""
    rows = (
        db.query(DBUserService.service_id)
        .filter(
            DBUserService.user_id == user.id,
            DBUserService.status == ServiceStatus.COMPLETED,
        )
        .all()
    )
    return {r[0] for r in rows}


def resolve_completed_titles(db: Session, title: str) -> set:
    """Return `title` plus every transitive mandatory prerequisite title.

    Keeps the document profile consistent: e.g. marking "NID Registration"
    as completed also implies "Citizenship Certificate Copy" and
    "Birth Certificate" are completed.
    """
    result = {title}
    changed = True
    while changed:
        changed = False
        for rule in db.query(PrerequisiteRule).filter(PrerequisiteRule.is_mandatory == True).all():  # noqa: E712
            service_title = rule.service.title
            prereq_title = rule.prerequisite_service.title
            if service_title in result and prereq_title not in result:
                result.add(prereq_title)
                changed = True
    return result


def get_prerequisite_status(db: Session, service, completed_ids: set):
    """Returns (prerequisites_met, missing_prerequisite_titles)."""
    rules = (
        db.query(PrerequisiteRule)
        .filter(
            PrerequisiteRule.service_id == service.id,
            PrerequisiteRule.is_mandatory == True,  # noqa: E712
        )
        .all()
    )
    missing = []
    for rule in rules:
        if rule.prerequisite_service_id not in completed_ids:
            missing.append(rule.prerequisite_service.title)
    return (len(missing) == 0), missing


def build_service_out(service, completed_ids: set, db: Session, lang: str = "en") -> GovServiceOut:
    """Build a GovServiceOut with prerequisite status filled in."""
    met, missing = get_prerequisite_status(db, service, completed_ids)
    ne = lang == "ne"
    return GovServiceOut(
        id=service.id,
        title=service.title_ne if ne and service.title_ne else service.title,
        category=service.category_ne if ne and service.category_ne else service.category,
        description=service.description_ne if ne and service.description_ne else service.description,
        guidance=service.guidance_ne if ne and service.guidance_ne else service.guidance,
        department=service.department,
        estimated_days=service.estimated_days,
        fee_npr=service.fee_npr,
        prerequisites_met=met,
        missing_prerequisites=missing,
    )


def build_application_out(db: Session, us: DBUserService, lang: str = "en") -> ApplicationOut:
    """Build an ApplicationOut for a UserService record, computing progress %."""
    steps = (
        db.query(DBProgress)
        .filter(DBProgress.user_service_id == us.id)
        .order_by(DBProgress.step_number)
        .all()
    )
    total = len(steps)
    done = sum(1 for s in steps if s.status == StepStatus.COMPLETED)
    percent = round((done / total) * 100) if total else 0
    localized = []
    for s in steps:
        step_out = ProgressStepOut.model_validate(s)
        if lang == "ne":
            step_out.step_name = s.step_name_ne or s.step_name
            step_out.step_description = s.step_description_ne or s.step_description
        localized.append(step_out)
    return ApplicationOut(
        application_id=us.id,
        service_id=us.service_id,
        service_title=(
            us.service.title_ne if lang == "ne" and us.service.title_ne else us.service.title
        ),
        status=us.status.value,
        progress_percent=percent,
        started_at=us.started_at,
        completed_at=us.completed_at,
        steps=localized,
    )


def get_recommended_next_step(db: Session, completed_ids: set, service_by_title: dict):
    """First incomplete document in the dependency chain whose prerequisites are met,
    or the fallback service when the whole chain is complete. Returns None if all done."""
    for title in NEXT_STEP_CHAIN:
        svc = service_by_title.get(title)
        if svc is None or svc.id in completed_ids:
            continue
        met, _ = get_prerequisite_status(db, svc, completed_ids)
        if met:
            return svc

    fallback = service_by_title.get(NEXT_STEP_FALLBACK)
    if fallback and fallback.id not in completed_ids:
        return fallback
    return None


# Simple structural layout for your service objects
class QueryRequest(BaseModel):
    question: Optional[str] = None
    query: Optional[str] = None
    message: Optional[str] = None
    debug: bool = False


# ── AUTHENTICATION ENDPOINTS ──────────────────────────────────────────────────

@app.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user account and return a JWT access token."""
    # Age gate: official documents (citizenship, NID, license, ...) require 16+
    today = date.today()
    dob = user_data.date_of_birth
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if dob > today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date of birth cannot be in the future."
        )
    if age < MIN_REGISTRATION_AGE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum age required: you must be at least {MIN_REGISTRATION_AGE} years old to register."
        )

    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    if user_data.citizenship_number:
        existing_citizenship = db.query(User).filter(User.citizenship_number == user_data.citizenship_number).first()
        if existing_citizenship:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this citizenship number already exists."
            )

    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        date_of_birth=user_data.date_of_birth,
        phone=user_data.phone,
        citizenship_number=user_data.citizenship_number,
        province=user_data.province
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": new_user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(new_user)
    )


@app.post("/auth/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user with email and password, returning a JWT token."""
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated."
        )

    token = create_access_token({"sub": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )


@app.get("/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Returns the profile of the currently logged-in user."""
    return UserOut.model_validate(current_user)


@app.get("/chat/history", response_model=ChatHistoryOut)
def get_chat_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return saved chatbot history for the authenticated user."""
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at)
        .all()

    )
    return ChatHistoryOut(
        user_id=current_user.id,
        messages=messages,
    )


# ── USER DOCUMENT VAULT ───────────────────────────────────────────────────────

def _document_out(doc: DBDocument) -> DocumentOut:
    """Convert a Document row to the API schema (tags string → list)."""
    tags = [t.strip() for t in (doc.tags or "").split(",") if t.strip()]
    return DocumentOut(
        id=doc.id,
        label=doc.label,
        tags=tags,
        description=doc.description,
        filename=doc.filename,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        created_at=doc.created_at,
    )


def _get_owned_document(db: Session, current_user: User, document_id: int) -> DBDocument:
    doc = db.query(DBDocument).filter(DBDocument.id == document_id).first()
    if doc is None or doc.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.post("/api/v1/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    label: str = Form(...),
    file: UploadFile = File(...),
    tags: Optional[str] = Form(""),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a document image/PDF into the authenticated user's vault."""
    label = (label or "").strip()
    if not label:
        raise HTTPException(status_code=422, detail="A label is required for the document.")
    if len(label) > 200:
        raise HTTPException(status_code=422, detail="Label is too long (max 200 characters).")

    mime = file.content_type or ""
    ext = ALLOWED_DOC_MIME.get(mime)
    if not ext:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Allowed: JPEG, PNG, WEBP, HEIC, PDF.",
        )

    content = await file.read()
    if len(content) > MAX_DOC_BYTES:
        raise HTTPException(status_code=413, detail="File is too large (max 10 MB).")
    if len(content) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    plain_size = len(content)
    content = encrypt_bytes(content)

    safe_filename = os.path.basename(file.filename or "document") or "document"
    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest = _user_doc_dir(current_user.id) / stored_name
    dest.write_bytes(content)

    doc = DBDocument(
        user_id=current_user.id,
        label=label,
        tags=(tags or "").strip(),
        description=(description or "").strip() or None,
        filename=safe_filename,
        stored_name=stored_name,
        mime_type=mime,
        size_bytes=plain_size,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _document_out(doc)


@app.get("/api/v1/documents", response_model=List[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the authenticated user's uploaded documents, newest first."""
    docs = (
        db.query(DBDocument)
        .filter(DBDocument.user_id == current_user.id)
        .order_by(DBDocument.created_at.desc())
        .all()
    )
    return [_document_out(d) for d in docs]


@app.patch("/api/v1/documents/{document_id}", response_model=DocumentOut)
def update_document(
    document_id: int,
    payload: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a document's label/tags/description."""
    doc = _get_owned_document(db, current_user, document_id)
    if payload.label is not None:
        doc.label = payload.label.strip()
    if payload.tags is not None:
        doc.tags = payload.tags.strip()
    if payload.description is not None:
        doc.description = payload.description.strip() or None
    db.commit()
    db.refresh(doc)
    return _document_out(doc)


@app.get("/api/v1/documents/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream the stored file back to the authenticated owner."""
    doc = _get_owned_document(db, current_user, document_id)
    file_path = DOC_STORAGE_DIR / str(current_user.id) / doc.stored_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing on server")

    raw = file_path.read_bytes()
    try:
        data = decrypt_bytes(raw)
    except ValueError:
        # Legacy unencrypted file written before encryption was enabled.
        data = raw
    return Response(
        content=data,
        media_type=doc.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )


@app.delete("/api/v1/documents/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document's metadata and its file from disk."""
    doc = _get_owned_document(db, current_user, document_id)
    file_path = DOC_STORAGE_DIR / str(current_user.id) / doc.stored_name
    if file_path.exists():
        file_path.unlink()
    db.delete(doc)
    db.commit()
    return {"detail": "Document deleted"}


def _user_doc_dir(user_id: int) -> Path:
    d = DOC_STORAGE_DIR / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── RAG CHATBOT ENDPOINT ──────────────────────────────────────────────────────

def _extract_llm_text(result) -> str:
    """Robustly pull the text out of an LLM response.

    Some reasoning models (e.g. gpt-oss-120b) return an AIMessage whose
    `.content` is empty and put the prose in a reasoning/extra field. Without
    this we'd fall back to `str(result)`, dumping the whole object into the UI.
    """
    content = getattr(result, "content", None)
    if isinstance(content, list):
        content = "\n".join(
            str(part.get("text", part)) if isinstance(part, dict) else str(part)
            for part in content
        )
    text = (content or "").strip()
    if text:
        return text

    for attr in ("reasoning_content",):
        val = getattr(result, attr, None)
        if val:
            return str(val).strip()

    extra = getattr(result, "additional_kwargs", {}) or {}
    for key in ("content", "reasoning_content", "reasoning"):
        val = extra.get(key)
        if val:
            return str(val).strip()

    return ""


@app.post("/ask", response_model=AskResponse)
async def ask_government_bot(
    request: QueryRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    user_question = request.question or request.query or request.message

    if not user_question:
        raise HTTPException(
            status_code=422,
            detail="Provide one of: 'question', 'query', or 'message' in JSON body.",
        )

    try:
        if current_user is not None:
            # Persist the user's question to chat history
            user_message = ChatMessage(
                user_id=current_user.id,
                role="user",
                content=user_question,
            )
            db.add(user_message)
            db.commit()
            db.refresh(user_message)

        # Detect query language (Nepali queries → Nepali answer, English → English)
        try:
            query_lang = detect(user_question)
        except LangDetectException:
            query_lang = "en"
        answer_lang = "NEPALI" if query_lang == "ne" else "ENGLISH"

        # Use hybrid retrieval (vector + lexical) to get documents and metadata.
        # Cross-lingual retrieval is weaker, so Nepali queries get a wider net AND,
        # for retrieval purposes only, the question is translated to English so it
        # matches the English knowledge base. The answer stays in the user's language.
        retrieval_k = MULTILINGUAL_RETRIEVER_K if query_lang == "ne" else retriever_k
        retrieval_question = _translate_to_english(user_question) if query_lang == "ne" else user_question
        docs = hybrid_retrieve(retrieval_question, retrieval_k)

        # Extract unique sources from metadata
        sources = []
        for d in docs:
            source_path = d.metadata.get("source", "Unknown Document")
            filename = os.path.basename(source_path)
            if filename not in sources:
                sources.append(filename)

        context = "\n\n".join(
            getattr(d, "page_content", "") for d in docs if getattr(d, "page_content", "")
        )

        # Concise-answer system prompt (English or Nepali), which asks the LLM
        # to reply in a strict JSON shape and point to the full guide instead of
        # reproducing the whole procedure.
        # NOTE: use .replace() (not str.format()) — the JSON template's braces
        # would be interpreted as format fields and raise a KeyError.
        prompt = SYSTEM_PROMPTS.get(answer_lang, SYSTEM_PROMPTS["ENGLISH"])
        prompt = prompt.replace("{context}", context).replace("{question}", user_question)

        llm_result = llm.invoke(prompt)
        raw_answer = _extract_llm_text(llm_result)

        # Parse the JSON reply, falling back to the raw text if malformed.
        parsed = parse_ask_json(raw_answer)
        answer_text = (parsed.get("answer") or raw_answer).strip()
        if not answer_text:
            answer_text = (
                "I couldn't find a clear answer. Please rephrase your question, "
                "or open the relevant guide for the full details."
            )

        if current_user is not None:
            # Persist only the answer text (never the raw JSON) so history
            # displays cleanly.
            assistant_message = ChatMessage(
                user_id=current_user.id,
                role="assistant",
                content=answer_text,
            )
            db.add(assistant_message)
            db.commit()
            db.refresh(assistant_message)

        # Map topic → the real gov_services row so the app can deep-link into
        # the guide detail screen (ids are not sequential across the catalog).
        guide_svc = resolve_guide_service(db, parsed.get("topic"))

        # Build the final response
        response_data = build_ask_response(
            parsed,
            sources,
            guide_service_id=guide_svc.id if guide_svc else None,
        )

        if request.debug:
            response_data["retrieved_chunks"] = [
                {
                    "metadata": getattr(d, "metadata", None),
                    "text_preview": (getattr(d, "page_content", "") or "")[:800],
                }
                for d in docs
            ]

        return response_data

    except Exception as e:
        error_text = str(e)
        if "401" in error_text or "Unauthorized" in error_text:
            raise HTTPException(
                status_code=401,
                detail="Invalid OpenRouter API key. Check your OPENROUTER_API_KEY in .env",
            ) from e
        if "Connection refused" in error_text or "Failed to connect" in error_text:
            raise HTTPException(
                status_code=503,
                detail="Cannot connect to OpenRouter. Check your internet connection and retry.",
            ) from e
        raise HTTPException(status_code=500, detail=error_text) from e


# ── ONBOARDING ENDPOINT ───────────────────────────────────────────────────────

@app.post("/api/v1/onboarding", response_model=OnboardingResponse)
def submit_onboarding(
    payload: OnboardingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    lang: str = Query("en"),
):
    """
    First-login onboarding: records the user's age and which government
    documents they have already completed, then builds a personal document
    dependency profile in user_services.
    """
    # Age is captured at registration via date_of_birth, so derive it here to
    # avoid asking twice. Fall back to the supplied age only when DOB is unknown
    # (e.g. Google sign-in, which has no DOB).
    if current_user.date_of_birth is not None:
        today = date.today()
        dob = current_user.date_of_birth
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    else:
        age = payload.age
    if age is None or age <= 0 or age > 130:
        raise HTTPException(status_code=400, detail="Please enter a valid age.")

    unknown = [k for k in payload.completed_documents if k not in ONBOARDING_DOCUMENTS]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown document keys: {unknown}")

    current_user.age = age
    current_user.onboarding_completed = True

    service_by_title = {s.title: s for s in db.query(DBGovService).all()}

    # Mark selected documents (and their mandatory prerequisites) as COMPLETED.
    # Deduplicate titles first so each service is processed only once.
    all_titles = set()
    for key in payload.completed_documents:
        all_titles |= resolve_completed_titles(db, ONBOARDING_DOCUMENTS[key])

    for title in all_titles:
        svc = service_by_title.get(title)
        if not svc:
            continue
        existing = (
            db.query(DBUserService)
            .filter_by(user_id=current_user.id, service_id=svc.id)
            .first()
        )
        if existing:
            existing.status = ServiceStatus.COMPLETED
        else:
            db.add(DBUserService(
                user_id=current_user.id,
                service_id=svc.id,
                status=ServiceStatus.COMPLETED,
            ))

    db.commit()

    completed_ids = get_completed_service_ids(db, current_user)
    rec = get_recommended_next_step(db, completed_ids, service_by_title)
    return OnboardingResponse(
        onboarding_completed=True,
        recommended_next_step=build_service_out(rec, completed_ids, db, lang) if rec else None,
    )


# ── SERVICE DETAIL ENDPOINT ───────────────────────────────────────────────────

@app.get("/api/v1/services/{service_id}", response_model=ServiceDetailOut)
def get_service_detail(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    lang: str = Query("en"),
):
    """
    Returns full detail for a single service including whether its
    prerequisites are satisfied. Drives the mobile "prerequisite blocked"
    flow: blocked services only allow informational/read-only viewing.
    """
    svc = db.query(DBGovService).filter(DBGovService.id == service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    completed_ids = get_completed_service_ids(db, current_user) if current_user else set()
    met, missing = get_prerequisite_status(db, svc, completed_ids)

    service_by_title = {s.title: s for s in db.query(DBGovService).all()}
    rec = get_recommended_next_step(db, completed_ids, service_by_title)

    application = None
    if current_user:
        existing_us = (
            db.query(DBUserService)
            .filter_by(user_id=current_user.id, service_id=svc.id)
            .first()
        )
        if existing_us and existing_us.status != ServiceStatus.NOT_STARTED:
            application = build_application_out(db, existing_us, lang)

    return ServiceDetailOut(
        service=build_service_out(svc, completed_ids, db, lang),
        prerequisites_met=met,
        missing_prerequisites=missing,
        recommended_next_step=build_service_out(rec, completed_ids, db, lang) if rec else None,
        application=application,
    )


# ── APPLICATION PROGRESS ENDPOINTS ────────────────────────────────────────────

@app.post("/api/v1/services/{service_id}/apply", response_model=ApplicationOut)
def start_application(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    lang: str = Query("en"),
):
    """
    Starts a new application for a service: creates a UserService record
    (status IN_PROGRESS) and a step-level progress checklist.
    """
    svc = db.query(DBGovService).filter(DBGovService.id == service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    completed_ids = get_completed_service_ids(db, current_user)
    met, missing = get_prerequisite_status(db, svc, completed_ids)
    if not met:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This service's prerequisites are not met. Complete first: "
                   + ", ".join(missing),
        )

    existing = (
        db.query(DBUserService)
        .filter_by(user_id=current_user.id, service_id=svc.id)
        .first()
    )
    if existing and existing.status == ServiceStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already completed this service.",
        )
    if existing:
        # Idempotent: an open application already exists, just return it.
        return build_application_out(db, existing, lang)

    us = DBUserService(
        user_id=current_user.id,
        service_id=svc.id,
        status=ServiceStatus.IN_PROGRESS,
        started_at=func.now(),
    )
    db.add(us)
    db.flush()

    template = get_step_template(svc.title)
    for idx, (name, desc) in enumerate(template["en"], start=1):
        ne = template["ne"][idx - 1] if idx - 1 < len(template["ne"]) else ("", "")
        db.add(DBProgress(
            user_service_id=us.id,
            step_number=idx,
            step_name=name,
            step_description=desc,
            step_name_ne=ne[0] or name,
            step_description_ne=ne[1] or desc,
            status=StepStatus.IN_PROGRESS if idx == 1 else StepStatus.PENDING,
        ))

    db.commit()
    db.refresh(us)
    return build_application_out(db, us, lang)


@app.get("/api/v1/applications", response_model=List[ApplicationOut])
def list_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    lang: str = Query("en"),
):
    """Returns all of the user's applications (user_service records) with
    step-level progress, newest first. Drives the profile "My Progress" list."""
    records = (
        db.query(DBUserService)
        .filter(DBUserService.user_id == current_user.id)
        .order_by(DBUserService.updated_at.desc())
        .all()
    )
    return [build_application_out(db, us, lang) for us in records]


@app.get("/api/v1/applications/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    lang: str = Query("en"),
):
    """Returns a user's application with its step-level progress."""
    us = (
        db.query(DBUserService)
        .filter(DBUserService.id == application_id, DBUserService.user_id == current_user.id)
        .first()
    )
    if not us:
        raise HTTPException(status_code=404, detail="Application not found")
    return build_application_out(db, us, lang)


@app.post(
    "/api/v1/applications/{application_id}/steps/{step_number}/complete",
    response_model=ApplicationOut,
)
def complete_application_step(
    application_id: int,
    step_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    lang: str = Query("en"),
):
    """
    Marks a step of the user's application as COMPLETED and advances the
    checklist. When all steps are done, the application itself is COMPLETED.
    """
    us = (
        db.query(DBUserService)
        .filter(DBUserService.id == application_id, DBUserService.user_id == current_user.id)
        .first()
    )
    if not us:
        raise HTTPException(status_code=404, detail="Application not found")
    if us.status == ServiceStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="This application is already completed.")

    step = (
        db.query(DBProgress)
        .filter(
            DBProgress.user_service_id == us.id,
            DBProgress.step_number == step_number,
        )
        .first()
    )
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    if step.status == StepStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="This step is already completed.")

    step.status = StepStatus.COMPLETED
    step.completed_at = func.now()

    steps = (
        db.query(DBProgress)
        .filter(DBProgress.user_service_id == us.id)
        .order_by(DBProgress.step_number)
        .all()
    )
    all_done = all(s.status == StepStatus.COMPLETED for s in steps)
    if all_done:
        us.status = ServiceStatus.COMPLETED
        us.completed_at = func.now()
    else:
        # Advance the next pending step to IN_PROGRESS.
        for s in steps:
            if s.status == StepStatus.PENDING:
                s.status = StepStatus.IN_PROGRESS
                break

    db.commit()
    db.refresh(us)
    return build_application_out(db, us, lang)


# ── DASHBOARD ENDPOINT ────────────────────────────────────────────────────────

@app.get("/api/v1/dashboard", response_model=DashboardOut)
async def get_dashboard_data(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    lang: str = Query("en"),
):
    """
    Fetches real service catalog and recommendations from SQLite database.
    Personalizes output (dependency profile, recommended next step) when a
    Bearer JWT token is present.
    """
    db_services = db.query(DBGovService).filter(DBGovService.is_active == True).all()  # noqa: E712
    service_by_title = {s.title: s for s in db_services}

    completed_ids = get_completed_service_ids(db, current_user) if current_user else set()

    catalog_out = [build_service_out(s, completed_ids, db, lang) for s in db_services]

    user_name = current_user.full_name if current_user else "Guest User"
    needs_onboarding = bool(current_user and not current_user.onboarding_completed)

    # Recommendation scoring algorithm based on DB
    # Only surface services the user has NOT already completed, ranked by how
    # actionable they are: (1) prerequisites satisfied first, then (2) position
    # in the dependency chain, then (3) identity docs priority, then title.
    en_titles = {s.id: s.title for s in db_services}
    candidates = [s for s in db_services if s.id not in completed_ids]

    def rec_rank(svc):
        title = en_titles[svc.id]
        chain_pos = next((i for i, t in enumerate(NEXT_STEP_CHAIN) if t == title), len(NEXT_STEP_CHAIN))
        met, _ = get_prerequisite_status(db, svc, completed_ids)
        prio = 0 if ("Passport" in title or "NID" in title) else 1
        return (0 if met else 1, chain_pos, prio, title)

    recommendations_out = sorted(candidates, key=rec_rank)[:2]
    for r in recommendations_out:
        r.is_recommended = True

    # Recommended next step from the dependency chain
    next_step = get_recommended_next_step(db, completed_ids, service_by_title)
    recommended_next_step = (
        build_service_out(next_step, completed_ids, db, lang) if next_step else None
    )

    return DashboardOut(
        user_name=user_name,
        services=catalog_out,
        recommendations=recommendations_out,
        needs_onboarding=needs_onboarding,
        recommended_next_step=recommended_next_step,
    )


@app.get("/")
def home():
    return {"status": "EasyGov API is Running"}


# ── GOVERNMENT OFFICES (Find Nearest Office) ─────────────────────────────────
from app.offices import router as offices_router  # noqa: E402

app.include_router(offices_router)


# ── GOOGLE SIGN-IN (Continue with Google) ────────────────────────────────────
from app.google_auth import router as google_auth_router  # noqa: E402

app.include_router(google_auth_router)


# ── ADMIN PORTAL ──────────────────────────────────────────────────────────────

@app.get("/admin/services", response_model=List[AdminServiceSummary])
def admin_list_services(
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    """List all services (active + inactive) for the admin dropdown."""
    rows = db.query(DBGovService).order_by(DBGovService.title).all()
    return [
        AdminServiceSummary(
            id=s.id,
            title=s.title,
            category=s.category,
            is_active=s.is_active,
        )
        for s in rows
    ]


@app.post("/admin/services/{service_id}", response_model=AdminIngestResult)
def admin_update_service(
    service_id: int,
    payload: AdminServiceUpdate,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    """Update a service's catalog fields; optionally re-index guidance into RAG."""
    svc = db.query(DBGovService).filter(DBGovService.id == service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    title_changed = False
    if payload.title is not None:
        svc.title = payload.title.strip()
        title_changed = True
    if payload.title_ne is not None:
        svc.title_ne = payload.title_ne.strip()
    if payload.category is not None:
        svc.category = payload.category.strip()
    if payload.category_ne is not None:
        svc.category_ne = payload.category_ne.strip()
    if payload.description is not None:
        svc.description = payload.description.strip() or None
    if payload.description_ne is not None:
        svc.description_ne = payload.description_ne.strip() or None
    if payload.guidance is not None:
        svc.guidance = payload.guidance.strip() or None
    if payload.guidance_ne is not None:
        svc.guidance_ne = payload.guidance_ne.strip() or None
    if payload.department is not None:
        svc.department = payload.department.strip()
    if payload.estimated_days is not None:
        svc.estimated_days = payload.estimated_days
    if payload.fee_npr is not None:
        svc.fee_npr = int(payload.fee_npr)
    if payload.is_active is not None:
        svc.is_active = payload.is_active

    db.commit()
    db.refresh(svc)

    folder = svc.title.lower().replace(" ", "_")
    if payload.reindex_rag and (svc.guidance or svc.guidance_ne):
        result = reindex_service_guidance(svc, folder, embeddings, vector_db)
        clear_corpus_cache()
        return AdminIngestResult(
            service=folder,
            version="guidance",
            indexed=result.get("indexed", 0),
            stats=result.get("stats"),
            message=result.get("message"),
        )

    return AdminIngestResult(
        service=folder,
        version="guidance",
        indexed=0,
        stats=None,
        message="Saved. RAG is unchanged — use the 'RAG Ingest' tab to update the chatbot's knowledge.",
    )


@app.post("/admin/ingest", response_model=AdminIngestResult)
def admin_ingest_document(
    service: str = Form(...),
    version: Optional[str] = Form("1.0"),
    replace_previous: bool = Form(False),
    file: UploadFile = File(...),
    _: bool = Depends(require_admin),
):
    """Upload a new/updated RAG source document (PDF/MD) for a service."""
    service_folder = (service or "").strip().lower().replace(" ", "_")
    if not service_folder:
        raise HTTPException(status_code=422, detail="A service folder is required.")

    data = file.file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    result = ingest_uploaded_document(
        service=service_folder,
        filename=file.filename or "document",
        data=data,
        version=version or "1.0",
        replace_previous=replace_previous,
        embeddings=embeddings,
        vector_db=vector_db,
    )
    clear_corpus_cache()
    return AdminIngestResult(
        service=service_folder,
        version=version or "1.0",
        indexed=result.get("indexed", 0),
        stats=result.get("stats"),
        message=result.get("message"),
    )


@app.get("/admin/ingest/list")
def admin_list_ingested(_: bool = Depends(require_admin)):
    """List every ingested source file (service folder + filename)."""
    return list_ingested_documents()


@app.delete("/admin/ingest", response_model=AdminIngestResult)
def admin_delete_ingested(
    service: str = Query(..., min_length=1),
    filename: str = Query(..., min_length=1),
    _: bool = Depends(require_admin),
):
    """Delete an ingested file and its chunks so the chatbot stops answering about it."""
    result = delete_ingested_document(service, filename, vector_db)
    clear_corpus_cache()
    return AdminIngestResult(
        service=result["service"],
        version=None,
        indexed=result.get("chunks_deleted", 0),
        stats=None,
        message=f"Deleted {result.get('chunks_deleted', 0)} chunk(s) and removed the file.",
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
