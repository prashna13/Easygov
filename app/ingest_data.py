import os
import re
from pathlib import Path
from dotenv import load_dotenv


from langchain_community.indexes._sql_record_manager import SQLRecordManager
from langchain_core.indexing import index
from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

load_dotenv()

# ── SOURCE NORMALISATION ──────────────────────────────────────────────────────
def _canonical_source(path: str) -> str:
    """Return a stable, absolute, lowercased source identifier so the
    SQLRecordManager recognises the same file across runs regardless of path
    casing or relative/absolute form."""
    try:
        return str(Path(path).resolve()).lower()
    except Exception:
        return str(path).lower()


# ── CHUNK TAG PARSER ──────────────────────────────────────────────────────────
def parse_chunk_tag(text: str) -> dict:
    """Extract chunk_id and topic from [CHUNK_TAG: ...] lines in the PDF."""
    match = re.search(
        r'\[CHUNK_TAG:\s*([^\|\]]+)\|?\s*topic:([^\|\]]+)\|?\s*source:([^\]]+)\]',
        text
    )
    if match:
        return {
            "chunk_id": match.group(1).strip(),
            "topic":    match.group(2).strip(),
            "doc_source": match.group(3).strip(),
        }
    return {}

# ── SERVICE DETECTOR ──────────────────────────────────────────────────────────
def detect_service_from_path(file_path: str, data_path: str) -> str:
    """
    Reads the subfolder name as the service tag.
    data_source/passport/file.pdf  → service: "passport"
    data_source/nid/file.pdf       → service: "nid"
    data_source/file.pdf           → service: "general"

    Resolves both paths to absolute before comparing — fixes Windows
    relative-vs-absolute mismatch errors.
    """
    try:
        abs_file = Path(file_path).resolve()
        abs_data = Path(data_path).resolve()
        rel = abs_file.relative_to(abs_data)
        parts = rel.parts
        return parts[0].lower() if len(parts) > 1 else "general"
    except ValueError:
        # Fallback: extract folder name directly from the raw path string
        # Handles edge cases where resolve() still mismatches on Windows
        parts = Path(file_path).parts
        data_parts = Path(data_path).parts
        # Find data_source in the path and take the next part as service
        for i, part in enumerate(parts):
            if part.lower() in [p.lower() for p in data_parts]:
                if i + 1 < len(parts) - 1:   # there's a subfolder after data_source
                    return parts[i + 1].lower()
        return "general"

# ── MAIN INGESTION ────────────────────────────────────────────────────────────
def ingest_docs():
    data_path            = "data_source/"
    persist_directory    = "db_storage/chroma_db"
    record_manager_db    = "sqlite:///db_storage/record_manager.db"

    # 1. Setup Embeddings
    model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    print(f"🔧 Loading embedding model: {model_name}")
    embeddings = HuggingFaceEmbeddings(model_name=model_name)

    # 2. Initialize Vector Store
    vector_db = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )

    # 3. Setup Record Manager (tracks file changes for incremental indexing)
    record_manager = SQLRecordManager(
        namespace="chroma/easygov",
        db_url=record_manager_db
    )
    record_manager.create_schema()

    # 4. Load Documents
    print(f"\n🔍 Scanning all subfolders in {data_path}...")

    pdf_loader = DirectoryLoader(
        data_path,
        glob="**/*.pdf",
        loader_cls=PyMuPDFLoader,
        recursive=True,
        show_progress=True
    )
    md_loader = DirectoryLoader(
        data_path,
        glob="**/*.md",
        loader_cls=UnstructuredMarkdownLoader,
        recursive=True,
        show_progress=True
    )

    all_docs = []
    try:
        all_docs.extend(pdf_loader.load())
        all_docs.extend(md_loader.load())
    except Exception as e:
        print(f"⚠️  Error during loading: {e}")

    if not all_docs:
        print("❌ No documents found! Make sure files are in data_source/ or its subfolders.")
        return

    print(f"📖 Loaded {len(all_docs)} raw pages.")

    # 5. Split into Chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", "।", ".", " ", ""]
    )
    chunks = text_splitter.split_documents(all_docs)
    print(f"✂️  Split into {len(chunks)} chunks.")

    # 6. Attach Service Metadata + Parse CHUNK_TAGs
    data_path_abs = str(Path(data_path).resolve())
    service_counts = {}

    for chunk in chunks:
        # Normalise the source path (absolute + lowercased) so the SQLRecordManager
        # recognises the same file across runs even if the path casing or
        # relative/absolute form differs — otherwise repeated ingestions duplicate
        # chunks (the record manager sees them as different sources).
        chunk.metadata["source"] = _canonical_source(chunk.metadata.get("source", ""))
        source_path = chunk.metadata["source"]

        # Detect service from subfolder name
        service = detect_service_from_path(source_path, data_path_abs)
        chunk.metadata["service"]  = service
        chunk.metadata["language"] = "en"
        chunk.metadata["version"]  = "1.0"

        # Parse CHUNK_TAG if present in the text
        tag_meta = parse_chunk_tag(chunk.page_content)
        if tag_meta:
            chunk.metadata.update(tag_meta)
            # Remove the [CHUNK_TAG: ...] line from the content itself
            chunk.page_content = re.sub(
                r'\[CHUNK_TAG:[^\]]+\]', '', chunk.page_content
            ).strip()

        service_counts[service] = service_counts.get(service, 0) + 1

    print(f"\n📂 Chunks by service:")
    for svc, count in sorted(service_counts.items()):
        print(f"   {svc:<20} {count} chunks")

    # 7. Incremental Indexing
    # Skips unchanged chunks, updates edited ones, adds new ones
    print(f"\n🚀 Syncing {len(chunks)} chunks to ChromaDB...")

    indexing_stats = index(
        chunks,
        record_manager,
        vector_db,
        cleanup="incremental",
        source_id_key="source"
    )

    print(f"\n✅ Ingestion Complete!")
    print(f"📊 Stats: {indexing_stats}")
    print(f"\n💡 Tip: To filter by service at query time:")
    print(f'   retriever = vector_db.as_retriever(search_kwargs={{"k":5, "filter":{{"service":"nid"}}}})')


if __name__ == "__main__":
    # Ensure required directories exist
    os.makedirs("data_source",       exist_ok=True)
    os.makedirs("db_storage",        exist_ok=True)
    ingest_docs()