# Architecture

## Frontend

React + Vite + Tailwind CSS provide the browser client.

## Backend

FastAPI will provide the HTTP API and application orchestration layer.

## Database

PostgreSQL is the application metadata and source-of-truth database. It will store users, documents, conversations, messages, and processing metadata.

## Vector Database

ChromaDB is the initial development vector database. The vector store is a semantic retrieval layer, not the authoritative source for application metadata.

## Embedding Model

Sentence Transformers will generate document and query embeddings in a later phase.

## LLM

The language-model provider is intentionally provider-agnostic and configured through environment variables.

## Authentication

JWT-based authentication will protect API resources, with authorization enforced server-side by role.

## RAG Flow

```text
College Documents
  -> Text Extraction
  -> Chunking
  -> Embeddings
  -> Vector Database
  -> Similarity Search
  -> Relevant Context
  -> LLM
  -> Answer + Sources
```

## System Boundary

```text
React Frontend
      |
      v
FastAPI Backend
      |
      +--> PostgreSQL (application metadata/source of truth)
      |
      +--> RAG Pipeline --> ChromaDB (semantic retrieval layer) --> LLM
```

Phase 0 establishes this boundary only; it does not implement application logic, models, migrations, authentication, ingestion, retrieval, or generation.
