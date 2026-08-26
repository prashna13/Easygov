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

    # Parse the saved file into LangChain Documents (PDF via PyMuPDF).
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
        _attach_meta(c, service, "en", version, c.metadata.get("source", str(dest)))

    stats = _index_chunks(chunks, embeddings, vector_db)
    logger.info("Ingested %s for service '%s' (%s chunks): %s", safe_name, service, len(chunks), stats)
    return {"indexed": len(chunks), "stats": stats}
