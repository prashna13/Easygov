from fastapi import FastAPI
from pydantic import BaseModel
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.chains import RetrievalQA
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

# 3. Initialize Gemini 1.5 Flash (The Reasoning Engine)
llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.2 # Lower temperature = more factual, less "creative"
)

# 4. Create the Retrieval Chain
# This connects the Vector DB search to the LLM
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vector_db.as_retriever(search_kwargs={"k": 3}) # Get top 3 chunks
)

class QueryRequest(BaseModel):
    question: str

@app.post("/ask")
async def ask_government_bot(request: QueryRequest):
    response = qa_chain.invoke(request.question)
    return {"answer": response["result"]}

@app.get("/")
def home():
    return {"status": "EasyGov API is Running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)