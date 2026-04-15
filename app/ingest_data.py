import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings # <--- New local import
from langchain_chroma import Chroma

# Load environment variables
load_dotenv()

def ingest_docs():
    # --- Configuration ---
    data_path = "data_source/"
    persist_directory = "db_storage/chroma_db"

    # --- 1. LOCAL EMBEDDING SETUP ---
    # This model is specifically built for 50+ languages, including Nepali.
    # It will download (~400MB) the first time you run it.
    print("🔍 Initializing Local Multilingual Model...")
    model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': 'cpu'} # Use 'cuda' if you have an NVIDIA GPU
        )
        print("✅ Local model loaded successfully!")
    except Exception as e:
        print(f"❌ Failed to load local model: {e}")
        return

    all_documents = []

    # --- 2. FILE CHECK ---
    if not os.path.exists(data_path):
        os.makedirs(data_path)
        print(f"📁 Created {data_path}. Add PDFs and run again.")
        return

    pdf_files = [f for f in os.listdir(data_path) if f.endswith(".pdf")]
    if not pdf_files:
        print(f"❌ No PDFs found in {data_path}. Please add your files.")
        return

    # --- 3. LOAD & SPLIT PDFs ---
    for file in pdf_files:
        print(f"📖 Processing: {file}...")
        try:
            loader = PyPDFLoader(os.path.join(data_path, file))
            data = loader.load()

            # Split into chunks (including the Nepali '।' separator)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=700,
                chunk_overlap=70,
                separators=["\n\n", "\n", "।", ".", " ", ""]
            )

            chunks = text_splitter.split_documents(data)
            all_documents.extend(chunks)
            print(f"   -> Split into {len(chunks)} chunks.")

        except Exception as e:
            print(f"⚠️ Error reading {file}: {e}")

    # --- 4. STORE IN CHROMADB ---
    if all_documents:
        print(f"🚀 Ingesting {len(all_documents)} chunks into ChromaDB (Local)...")
        
        # We delete old DB if it exists to ensure a clean start
        vector_db = Chroma.from_documents(
            documents=all_documents,
            embedding=embeddings,
            persist_directory=persist_directory
        )
        
        print(f"🎉 SUCCESS! Local Brain updated at: {persist_directory}")
    else:
        print("❌ No text found to ingest.")

if __name__ == "__main__":
    ingest_docs()