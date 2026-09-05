"""
admin_utils.py
--------------
Helpers for the admin portal: admin-token auth, guide re-indexing into the RAG
vector store, and ingestion of new versioned source documents.

These functions accept the already-loaded `embeddings` and `vector_db` from
app.main so the FastAPI process does not reload the model on every request.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import Header, HTTPException, status
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document
from langchain_core.indexing import index
from langchain_community.indexes._sql_record_manager import SQLRecordManager
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

DATA_SOURCE_DIR = Path("data_source")
RECORD_MANAGER_DB = "sqlite:///db_storage/record_manager.db"

# Allowed source document extensions (match app/ingest_data.py).
ALLOWED_EXT = (".pdf", ".md")


def _admin_token() -> str:
    """Read the token lazily so it picks up values loaded by `dotenv` at startup.

    (main.py imports this module before calling load_dotenv(), so a module-level
    `os.getenv` would always be empty.)
    """
    return os.getenv("ADMIN_TOKEN", "")


def require_admin(x_admin_token: str = Header(default="", alias="X-Admin-Token")):
    """FastAPI dependency gating all /admin routes on the ADMIN_TOKEN env var."""
    token = _admin_token()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API is not configured (set ADMIN_TOKEN in .env).",
        )
    if x_admin_token != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token.",
        )
    return True


def _canonical_source(path: str) -> str:
    """Return a stable, absolute, lowercased source identifier so the
    SQLRecordManager recognises the same file across runs regardless of path
    casing or relative/absolute form."""
    try:
        return str(Path(path).resolve()).lower()
    except Exception:
        return str(path).lower()


def _splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", "।", ".", " ", ""],
    )


def _index_chunks(chunks, embeddings, vector_db):
    """Run LangChain incremental indexing over the given chunks.

    `cleanup="incremental"` + `source_id_key="source"` means unchanged chunks
    are skipped, edited ones updated, new ones added, and chunks whose source
    disappeared are removed — so re-ingesting a new file version replaces the
    old content instead of duplicating it.
    """
    record_manager = SQLRecordManager(
        namespace="chroma/easygov",
        db_url=RECORD_MANAGER_DB,
    )
    record_manager.create_schema()
    return index(
        chunks,
        record_manager,
        vector_db,
        cleanup="incremental",
        source_id_key="source",
    )


def _attach_meta(chunk, service: str, lang: str, version: str, source: str) -> Document:
    chunk.metadata["service"] = service
    chunk.metadata["language"] = lang
    chunk.metadata["version"] = version
    chunk.metadata["source"] = source
    return chunk


def reindex_service_guidance(service, folder: str, embeddings, vector_db) -> dict:
    """Chunk a service's guidance (EN + NE) into the vector store.

    Uses a stable source id (`guidance:<id>:<lang>`) so editing the guide and
    re-running replaces the old chunks. Returns the indexing stats.
    """
    chunks = []
    splitter = _splitter()
    version = "guidance"
    for lang, text in (("en", service.guidance), ("ne", service.guidance_ne)):
        if not text or not text.strip():
            continue
        source = f"guidance:{service.id}:{lang}"
        doc = Document(page_content=text, metadata={"source": source})
        for c in splitter.split_documents([doc]):
            chunks.append(_attach_meta(c, folder, lang, version, source))

    if not chunks:
        return {"indexed": 0, "message": "No guidance text to index."}

    stats = _index_chunks(chunks, embeddings, vector_db)
    logger.info("Re-indexed guidance for service %s (%s chunks): %s", service.id, len(chunks), stats)
    return {"indexed": len(chunks), "stats": stats}


def ingest_uploaded_document(
    service: str,
    filename: str,
    data: bytes,
    version: str,
    replace_previous: bool,
    embeddings,
    vector_db,
) -> dict:
    """Save a new/updated source document and index it (or its replacement)."""
    safe_name = os.path.basename(filename).strip().replace(" ", "_") or "document"
    if not safe_name.lower().endswith(ALLOWED_EXT):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only .pdf and .md source documents are supported.",
        )

    service_dir = DATA_SOURCE_DIR / service
    service_dir.mkdir(parents=True, exist_ok=True)

    if replace_previous:
        # Remove previously-ingested source files for this service (keep the
        # auto-generated per-service guidance snapshot, if any).
        for p in service_dir.glob("*"):
            if p.is_file() and not p.name.startswith("guidance"):
                p.unlink()

    dest = service_dir / safe_name
    dest.write_bytes(data)

    # Parse the saved file into document objects (PDF or markdown format).
    if safe_name.lower().endswith(".md"):
        text = data.decode("utf-8", errors="ignore")
        docs = [Document(page_content=text, metadata={"source": str(dest)})]
    else:
        docs = PyMuPDFLoader(str(dest)).load()

    if not docs:
        return {"indexed": 0, "message": "No text could be extracted from the file."}

    chunks = _splitter().split_documents(docs)
    version = version or "1.0"
    for c in chunks:
        source = _canonical_source(c.metadata.get("source") or str(dest))
        _attach_meta(c, service, "en", version, source)

    stats = _index_chunks(chunks, embeddings, vector_db)
    logger.info("Ingested %s for service '%s' (%s chunks): %s", safe_name, service, len(chunks), stats)
    return {"indexed": len(chunks), "stats": stats}


# ── LIST / DELETE INGESTED FILES ──────────────────────────────────────────────

def list_ingested_documents() -> list[dict]:
    """List every file currently under data_source/ (service folder + file)."""
    out = []
    if not DATA_SOURCE_DIR.is_dir():
        return out
    for svc_dir in sorted(DATA_SOURCE_DIR.iterdir()):
        if not svc_dir.is_dir():
            continue
        service = svc_dir.name.lower()
        for f in sorted(svc_dir.iterdir()):
            if f.is_file():
                out.append({
                    "service": service,
                    "filename": f.name,
                    "size_bytes": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })
    return out


def delete_ingested_document(service: str, filename: str, vector_db) -> dict:
    """Delete an ingested file AND its chunks from the vector store.

    The chatbot answers from the vector store, so once its chunks are gone it can
    no longer answer about the deleted document. The source file is also removed.
    """
    service_folder = (service or "").strip().lower().replace(" ", "_")
    if not service_folder:
        raise HTTPException(status_code=422, detail="A service folder is required.")

    svc_dir = DATA_SOURCE_DIR / service_folder
    target = None
    if svc_dir.is_dir():
        for f in svc_dir.iterdir():
            if f.is_file() and f.name.lower() == (filename or "").lower():
                target = f
                break
    if target is None:
        raise HTTPException(status_code=404, detail="File not found in that service folder.")

    # Remove every chunk whose canonical source points at this file. Count first
    # (since vector delete(where=...) returns None), then delete by explicit ids.
    source = _canonical_source(str(target))
    chunks_deleted = 0
    try:
        matching = vector_db.get(where={"source": source})
        chunk_ids = matching.get("ids") or []
        if chunk_ids:
            vector_db.delete(ids=chunk_ids)
        chunks_deleted = len(chunk_ids)
    except Exception as exc:  # noqa: BLE001 - never block deletion on a store failure
        logger.warning("Vector-store delete failed for %s: %s", source, exc)

    target.unlink(missing_ok=True)
    logger.info("Deleted ingested file %s (%s chunk(s))", source, chunks_deleted)
    return {"service": service_folder, "filename": target.name, "chunks_deleted": chunks_deleted}
