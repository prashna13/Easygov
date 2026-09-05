# 🇳🇵 EasyGov Nepal

> **AI-Powered Navigation & Automated Workflow Tracking for Public Services in Nepal**

EasyGov Nepal is an end-to-end digital governance assistant and service navigation platform designed to simplify access to government services in Nepal—including **Passport (E-Passport)**, **National ID (NID)**, **Citizenship**, **Driving License**, **Business Registration**, **PAN**, and more. 

The platform combines a **Multilingual RAG (Retrieval-Augmented Generation) AI Chatbot**, an **Automated Prerequisite & Step Progress Tracker**, a **Secure Encrypted Private Document Vault**, a **Native Kotlin Android Mobile Application**, a **Streamlit Web Portal & Admin Control Panel**, and an **In-house RAGAS Evaluation Suite**.

---

## 🌟 Key Features

### 🤖 Multilingual AI Chatbot (RAG-Driven)
* **Context-Aware Assistance:** Uses hybrid retrieval (Chroma vector search + term lexical fallback) over curated official government guidelines.
* **Bilingual Support:** Understands and responds in both **English** and **Nepali** (via automatic language detection using `langdetect`).
* **Source Attribution:** Cites specific ingested document sources alongside responses.

### 📋 Prerequisite & Progress Tracking Engine
* **Dependency Validation:** Enforces prerequisites (e.g., citizenship required before applying for a passport or NID).
* **Step-by-Step Guidance:** Interactive checklists for required documents, office visits, online forms, and fees.
* **Status Lifecycle:** Tracks application states (`NOT_STARTED`, `IN_PROGRESS`, `SUBMITTED`, `COMPLETED`).

### 🔐 Encrypted Private Document Vault
* **Security First:** User documents (citizenship scans, photographs, forms) are stored using secure encryption (`doc_crypto`).
* **Instant Verification:** Easily attach stored vault documents to service steps.

### 📱 Native Android Application (`Easygov_mobile`)
* Built with modern **Kotlin**, **Jetpack Navigation**, **Material Design 3**, **Retrofit**, and **View Binding**.
* Features interactive service catalog, live onboarding flow, offline session management, dynamic server URL configuration, chatbot interface with history drawer, and GIS location finder for nearby government offices.

### 🛠️ Streamlit Admin Portal & Web UI
* **User Web Assistant (`app/frontend.py`):** Lightweight web-based search and assistant interface.
* **Admin Management (`app/admin_app.py`):** Update service metadata, modify guidance text with auto-reindexing into vector storage, and ingest new source PDFs/Markdown files.

### 📊 RAGAS-Style RAG Evaluation Harness (`eval/`)
* In-house evaluation suite evaluating 5 core metrics: **Faithfulness**, **Answer Relevance**, **Correctness**, **Context Precision**, and **Context Recall**.
* Automated regression gating using locked baselines (`baseline.json`).

---

## 🛠️ Architecture & Tech Stack

```
                     ┌────────────────────────────────────────┐
                     │          Native Android App            │
                     │          (Kotlin / Material 3)         │
                     └───────────────────┬────────────────────┘
                                         │ REST API (JSON)
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             FastAPI Backend                                 │
│  ┌────────────────────┐  ┌───────────────────────┐  ┌────────────────────┐  │
│  │   Auth & Models    │  │  Prerequisite Engine  │  │ Encrypted Vault    │  │
│  │ (JWT / SQLAlchemy) │  │  & Step Tracking      │  │ (doc_crypto)       │  │
│  └────────────────────┘  └───────────────────────┘  └────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                            RAG Pipeline                               │  │
│  │  HuggingFace Embeddings ──▶ Chroma Vector DB ──▶ OpenRouter LLM       │  │
│  │  (paraphrase-multilingual)      (Hybrid Search)     (gpt-oss-120b)    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────┬────────────────────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
        ┌───────────────────────┐                 ┌───────────────────────┐
        │ Streamlit Web & Admin │                 │  SQLite / Chroma DB   │
        │    Control Panel      │                 │     Persistence       │
        └───────────────────────┘                 └───────────────────────┘
```

| Component | Technology / Library |
|---|---|
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/), [Pydantic v2](https://docs.pydantic.dev/) |
| **Database & ORM** | [SQLite](https://www.sqlite.org/), [SQLAlchemy](https://www.sqlalchemy.org/) |
| **AI / RAG Stack** | [LangChain](https://www.langchain.com/), [ChromaDB](https://www.trychroma.com/), [HuggingFace Embeddings](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2), [OpenRouter LLM](https://openrouter.ai/) |
| **Language Detection** | `langdetect` |
| **Security & Auth** | Passlib (bcrypt), PyJWT, Cryptography (AES document encryption) |
| **Android App** | Kotlin, Android SDK, Retrofit2, OkHttp3, Material 3, AndroidX Navigation |
| **Web & Admin UI** | [Streamlit](https://streamlit.io/) |
| **Testing & Eval** | Pytest, Custom RAGAS Evaluation Framework |

---

## 📁 Repository Structure

```
EasyGov_project/
├── app/                        # FastAPI Backend & Core Logic
│   ├── admin_app.py            # Streamlit Admin Portal
│   ├── admin_utils.py          # Document ingestion & reindexing handlers
│   ├── ask_utils.py            # RAG prompts and response formatting
│   ├── auth_utils.py           # JWT generation, password hashing & verification
│   ├── database.py             # SQLAlchemy session & DB initialization
│   ├── doc_crypto.py           # AES encryption for user document vault
│   ├── frontend.py             # Streamlit User Web Assistant
│   ├── geo.py                  # Distance calculation & office location helper
│   ├── google_auth.py          # Google OAuth validation helpers
│   ├── ingest_data.py          # Knowledge base ingestion script
│   ├── main.py                 # FastAPI application routes & endpoints
│   ├── models.py               # SQLAlchemy database models
│   ├── office_seed_data.py     # Government office location dataset
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── seed_data.py            # Initial service catalog seed data
│   └── step_templates.py       # Workflow templates for service steps
├── Easygov_mobile/             # Native Android Application (Kotlin)
│   ├── app/                    # Android app module (Source, XML layouts, Gradle)
│   └── build.gradle.kts        # Root Gradle build script
├── data_source/                # Curated knowledge base source documents
│   ├── Citizenship/
│   ├── Driving License/
│   ├── NID/
│   ├── Passport/
│   └── business_registration/
├── db_storage/                 # Persistent SQLite DB and Chroma Vector store
├── eval/                       # RAG Evaluation Framework (RAGAS-style)
│   ├── qa_dataset.jsonl        # 31 QA items (English + Nepali)
│   ├── metrics.py              # LLM-as-a-judge metric calculations
│   ├── pipeline.py             # Evaluation pipeline reusing production RAG path
│   └── run_eval.py             # Evaluation runner & regression gate
├── tests/                      # Pytest unit and integration test suite
├── .env                        # Environment configuration (Keys, DB paths)
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites
* **Python**: `3.10` or higher
* **Android Studio**: Ladybug / Jellyfish (for mobile development)
* **OpenRouter API Key**: Required for RAG chatbot responses ([Get key here](https://openrouter.ai/))

---

### 2. Backend Setup (FastAPI)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/EasyGov.git
   cd EasyGov
   ```

2. **Create and activate a virtual environment:**
   ```powershell
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables (`.env`):**
   Create or edit the `.env` file in the root directory:
   ```env
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   OPENROUTER_MODEL=openai/gpt-oss-120b
   ADMIN_TOKEN=your_admin_secret_token
   SECRET_KEY=your_jwt_secret_key
   EASYGOV_LITE=0
   ```

5. **Initialize Database & Ingest Knowledge Base:**
   ```bash
   python app/ingest_data.py
   ```

6. **Run the Backend Server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   * Interactive API Documentation (Swagger UI): `http://127.0.0.1:8000/docs`

---

### 3. Streamlit Portals

* **User Web Assistant:**
  ```bash
  streamlit run app/frontend.py
  ```
* **Admin Portal (Catalog Management & Document Ingestion):**
  ```bash
  streamlit run app/admin_app.py
  ```

---

### 4. Android Mobile Application Setup

1. Open the `Easygov_mobile` directory in **Android Studio**.
2. Sync Project with Gradle Files.
3. Configure Backend IP:
   * When running on an Android Emulator connecting to local host, the app uses `http://10.0.2.2:8000`.
   * For physical devices, set your local machine's IP address inside the app's server configuration settings dialog.
4. Build and Run on an Emulator or connected Android device (API Level 24+).

---

## 🧪 Testing & RAG Evaluation

### Running Unit & Integration Tests
Tests run in `EASYGOV_LITE=1` mode to bypass heavy ML model initialization for instant execution:
```bash
pytest
```

### Running RAG Evaluation (RAGAS Metrics)
To run the automated 5-metric evaluation against the test dataset:
```bash
# Run full evaluation suite
python eval/run_eval.py

# Quick test run on 5 items
python eval/run_eval.py --limit 5
```

#### Evaluation Metrics Summary
| Metric | Threshold | Target Description |
|---|---|---|
| **Faithfulness** | ≥ 0.80 | Ensures response is strictly grounded in retrieved documents |
| **Answer Relevance** | ≥ 0.70 | Measures how directly the response addresses the prompt |
| **Context Precision** | ≥ 0.70 | Evaluates signal-to-noise ratio of retrieved vector chunks |
| **Context Recall** | ≥ 0.70 | Measures coverage of ground-truth claims |
| **Correctness** | ≥ 0.60 | Verifies semantic alignment with official references |

---

## 📡 API Endpoints Overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/register` | User registration |
| `POST` | `/login` | Authenticate & get JWT token |
| `GET` | `/services` | List all government services & prerequisite status |
| `GET` | `/services/{id}` | Get detailed service guidance, steps, & requirements |
| `POST` | `/services/{id}/start` | Start tracking a service application |
| `POST` | `/ask` | Query the RAG AI chatbot (English & Nepali) |
| `GET` | `/offices` | Fetch nearby government offices with GIS filtering |
| `POST` | `/documents` | Upload & encrypt document to private vault |
| `GET` | `/documents` | List user's encrypted private documents |
| `GET` | `/admin/services` | List services (Admin authentication required) |
| `POST` | `/admin/ingest` | Ingest new document into Chroma vector store |

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:
1. Fork the project repository.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
