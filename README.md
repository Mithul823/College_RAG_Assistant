# College RAG Assistant

## Project Description

College RAG Assistant is a Retrieval-Augmented Generation system for answering college-related questions using administrator-approved institutional documents and providing supporting sources.

## Architecture

```text
React + Vite + Tailwind
          |
       FastAPI
          |
     RAG Pipeline
          |
    Vector Database
          |
          LLM
```

PostgreSQL is the authoritative store for application metadata. The vector database is the semantic retrieval layer.

## Development Phases

- Phase 0 - Project Initialization
- Phase 1 - Backend Foundation
- Phase 2 - Authentication
- Phase 3 - Document Processing
- Phase 4 - Embeddings + Vector Database
- Phase 5 - RAG
- Phase 6 - Chat
- Phase 7 - Frontend Integration
- Phase 8 - Admin Dashboard
- Phase 9 - Evaluation
- Phase 10 - Deployment

## Current Status

Phase 7 - Complete

The repository structure, frontend toolchain, FastAPI foundation, environment-backed configuration, SQLAlchemy session layer, Alembic wiring, structured logging, user authentication, PDF validation & storage, page-aware text extraction, text cleaning, section-aware chunking, admin document management APIs, Sentence-Transformers embedding provider, ChromaDB vector store, RAG retriever with relevance threshold filtering, structured prompt & context builder, provider-agnostic LLM integration, end-to-end evidence-grounded RAG engine, conversation management, multi-turn history tracking, message source citation persistence, authenticated `/api/v1/chat` and `/api/v1/conversations` APIs, React 19 / Vite / Tailwind frontend integration (Student Chat interface, Login/Register auth views, session management, multi-turn conversation history sidebar, answer mode badges, and interactive source citation inspector) are ready. The Admin document management dashboard and system metrics interface begin in Phase 8.

## Phase 7 Verification

From the repository root, run:

```powershell
# Backend automated test suite & bytecode verification
conda run -n college-rag-assistant python -m pytest backend\tests -v
conda run -n college-rag-assistant python -m compileall -q backend\app backend\alembic
conda run -n college-rag-assistant alembic -c backend\alembic.ini upgrade head --sql

# Frontend production bundle verification
cd frontend
npm run build
```

The Phase 7 checks pass locally (38 backend tests passing, frontend Vite production build passing). Apply migrations with `alembic upgrade head` after the configured PostgreSQL database is reachable.

## Prerequisites

- Python 3.11 or 3.12
- Node.js and npm
- PostgreSQL
- Git

## Local Environment

Create a private environment file before running the application:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and replace every `CHANGE_ME` value and the placeholder Supabase URL with your own credentials. Keep `.env` private; it is ignored by Git. Use `LLM_PROVIDER=gemini` and set `LLM_MODEL` and `LLM_API_KEY` to enable Gemini. `MIN_RELEVANCE_SCORE` is a numeric retrieval threshold, such as `0.55`, not an API key.

## Layout

- `backend/` - FastAPI service, ingestion pipeline, embeddings, vector store, RAG retrieval & generation, chat & conversations, domain models, and migrations
- `frontend/` - React/Vite/Tailwind client, auth views, chat workspace, conversation sidebar, and source inspector drawer
- `data/` - local upload and vector-store placeholders
- `docs/` - architecture and system documentation
- `tests/` - test suites and evaluation benchmarks

See [docs/architecture.md](docs/architecture.md) for the intended system design.
