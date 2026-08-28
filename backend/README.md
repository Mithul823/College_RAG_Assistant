# Backend

The backend provides the FastAPI service for College RAG Assistant through Phase 6, including authentication, document ingestion, embeddings, vector search, RAG generation, chat, and conversation history.

## Environment

Use the project Conda environment with Python 3.12:

```powershell
conda env create --file ..\environment.yml
conda activate college-rag-assistant
python --version
```

Install backend dependencies and run the service:

```powershell
conda activate college-rag-assistant
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

The health check is available at `http://127.0.0.1:8000/health`. Database migrations use the configured `DATABASE_URL`:

```powershell
alembic upgrade head
```

Authentication endpoints are available at `/api/v1/auth/register`, `/api/v1/auth/login`, and `/api/v1/auth/me`.
Chat and conversation endpoints are available at `/api/v1/chat` and `/api/v1/conversations`.
