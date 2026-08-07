import sys
import os

# Ensure project root is in sys.path when script is executed directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from app.database import get_db
from app.models import User, GovService as DBGovService, UserService as DBUserService, ChatMessage
from app.schemas import (
    UserRegister, UserLogin, UserOut, TokenResponse,
    DashboardOut, GovServiceOut, ChatHistoryOut
)
from app.auth_utils import (
    hash_password, verify_password, create_access_token,
    get_current_user, get_current_user_optional
)

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


# ── RAG CHATBOT ENDPOINT ──────────────────────────────────────────────────────

@app.post("/ask")
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

        if current_user is not None:
            assistant_message = ChatMessage(
                user_id=current_user.id,
                role="assistant",
                content=answer_text,
            )
            db.add(assistant_message)
            db.commit()
            db.refresh(assistant_message)

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


# ── DASHBOARD ENDPOINT ────────────────────────────────────────────────────────

@app.get("/api/v1/dashboard", response_model=DashboardOut)
async def get_dashboard_data(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Fetches real service catalog and recommendations from SQLite database.
    Personalizes output if Bearer JWT token is present.
    """
    db_services = db.query(DBGovService).filter(DBGovService.is_active == True).all()

    catalog_out = [
        GovServiceOut(
            id=s.id,
            title=s.title,
            category=s.category,
            description=s.description,
            department=s.department,
            estimated_days=s.estimated_days,
            fee_npr=s.fee_npr
        )
        for s in db_services
    ]

    user_name = current_user.full_name if current_user else "Guest User"

    # Recommendation scoring algorithm based on DB
    # Priority: Identity & Passport/NID services first
    recommendations_out = []
    if catalog_out:
        # Pick NID & Passport or top 2 services as recommendations
        rec_list = sorted(
            catalog_out,
            key=lambda x: 0 if "Passport" in x.title or "NID" in x.title else 1
        )
        recommendations_out = rec_list[:2]
        for r in recommendations_out:
            r.is_recommended = True

    return DashboardOut(
        user_name=user_name,
        services=catalog_out,
        recommendations=recommendations_out
    )


@app.get("/")
def home():
    return {"status": "EasyGov API is Running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
