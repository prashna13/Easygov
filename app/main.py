from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="EasyGov Nepal API")

# 1. Setup the same Local Embeddings as Day 2
model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
embeddings = HuggingFaceEmbeddings(model_name=model_name)

# 2. Load the existing ChromaDB from disk
vector_db = Chroma(
    persist_directory="db_storage/chroma_db",
    embedding_function=embeddings
)

# 3. Initialize OpenRouter LLM
openrouter_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b")
openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
print(f"[EasyGov] Using OpenRouter model: {openrouter_model} @ {openrouter_base_url}")

llm = ChatOpenAI(
    model=openrouter_model,
    base_url=openrouter_base_url,
    api_key=openrouter_api_key,
    temperature=0.2,
)

# 4. Retrieval settings (RAG)
retriever_k = int(os.getenv("RETRIEVER_K", "6"))


class QueryRequest(BaseModel):
    question: str | None = None
    query: str | None = None
    message: str | None = None
    debug: bool = False


@app.post("/ask")
async def ask_government_bot(request: QueryRequest):
    user_question = request.question or request.query or request.message

    if not user_question:
        raise HTTPException(
            status_code=422,
            detail="Provide one of: 'question', 'query', or 'message' in JSON body.",
        )

    try:
        # Use similarity_search() to get documents and metadata
        docs = vector_db.similarity_search(user_question, k=retriever_k)

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

        strict_prompt = (
            "You are EasyGov Nepal, a professional government assistant.\n"
            "Your task is to provide a structured, bulleted answer in ENGLISH based on the CONTEXT provided.\n"
            "Follow these rules:\n"
            "1. Translate any Nepali information from the context into clear English.\n"
            "2. Use bullet points and bold headers for readability.\n"
            "3. If the context is missing specific details, state clearly: 'I couldn't find that specific info.'\n"
            "4. Do not guess or use external knowledge.\n\n"
            f"CONTEXT (might be in Nepali or English):\n{context}\n\n"
            f"QUESTION:\n{user_question}\n"
            "ANSWER IN ENGLISH:"
        )

        llm_result = llm.invoke(strict_prompt)
        answer_text = getattr(llm_result, "content", None) or str(llm_result)

        # Build the final response
        response_data = {
            "answer": answer_text,
            "sources": sources
        }

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


@app.get("/")
def home():
    return {"status": "EasyGov API is Running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)