# College RAG Assistant

## Development-Ready Technical Specification

**Project:** Evidence-Grounded College Information Assistant
**Version:** 1.0.0
**Status:** Development Ready
**Architecture:** Full-stack RAG application
**Backend:** Python + FastAPI
**Frontend:** React + Vite + Tailwind CSS
**Primary Database:** PostgreSQL
**Vector Database:** ChromaDB for development, Qdrant-compatible architecture for production
**Authentication:** JWT
**LLM:** Provider-agnostic
**Embedding:** Sentence Transformers
**Deployment:** Docker-ready

---

# 1. Product Definition

## 1.1 Purpose

Build a web application that allows authenticated students to ask questions about college information.

The system retrieves information from administrator-approved college documents and generates answers using Retrieval-Augmented Generation (RAG).

The system must provide evidence for generated answers.

The system must refuse to answer when sufficiently relevant information cannot be retrieved.

---

# 2. Core Product Principle

The system is **not** a general-purpose AI chatbot.

The system is an **evidence-grounded information retrieval system**.

The following rule is mandatory:

> The LLM must not be treated as the source of truth for college-specific information.

The knowledge base is the source of truth.

If the knowledge base does not contain sufficient evidence, the system must respond with an explicit "information unavailable" response.

---

# 3. Scope

## 3.1 MVP Features

The first production-capable version MUST contain:

* User registration
* User login
* JWT authentication
* Student role
* Admin role
* Student chat interface
* Conversation history
* PDF upload
* PDF validation
* PDF text extraction
* Page-aware chunking
* Metadata storage
* Embedding generation
* Vector database
* Semantic retrieval
* Relevance threshold
* LLM generation
* Grounded answers
* Source citations
* Unknown-question handling
* Admin document listing
* Admin document deletion
* Document processing status
* PostgreSQL integration
* Frontend/backend integration
* Error handling
* API documentation
* Automated tests
* Docker development environment

## 3.2 Version 1.1

After MVP is stable:

* Hybrid retrieval
* Keyword/BM25 search
* Metadata filtering
* Reranking
* Feedback
* Source preview
* Admin analytics
* Document versioning

## 3.3 Version 2

Optional:

* OCR
* Multilingual support
* Streaming responses
* Voice input
* Voice output
* Advanced analytics
* Evaluation dashboard
* Automatic FAQ generation

---

# 4. Explicit Non-Goals for MVP

Do NOT implement these during the first MVP:

* Voice
* OCR
* Multiple LLM providers simultaneously
* Complex agentic workflows
* Web browsing
* Autonomous document discovery
* Fine-tuning
* Multi-agent architecture
* Recommendation systems
* Complex analytics
* Mobile application

The MVP must first prove that the RAG pipeline works correctly.

---

# 5. User Roles

## 5.1 Student

Permissions:

* Register
* Login
* Logout
* Create conversation
* Ask questions
* View answers
* View sources
* View own conversations
* Delete own conversations

Students MUST NOT:

* Upload documents
* Delete documents
* View admin analytics
* Access admin APIs

## 5.2 Admin

Permissions:

* Login
* Upload documents
* View documents
* Delete documents
* View processing status
* View basic statistics

Admin privileges must be enforced server-side.

Never rely solely on frontend route protection.

---

# 6. System Architecture

```text
                    ┌─────────────────────┐
                    │       Student       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   React Frontend    │
                    │   Vite + Tailwind   │
                    └──────────┬──────────┘
                               │ HTTP/JSON
                               ▼
                    ┌─────────────────────┐
                    │      FastAPI        │
                    │      Backend        │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       Authentication      PostgreSQL       RAG Service
                                                │
                                                ▼
                                         Query Processing
                                                │
                                                ▼
                                         Embedding Model
                                                │
                                                ▼
                                         Vector Database
                                                │
                                                ▼
                                         Top-K Chunks
                                                │
                                                ▼
                                         Relevance Filter
                                                │
                                                ▼
                                         Context Builder
                                                │
                                                ▼
                                               LLM
                                                │
                                                ▼
                                     Answer + Source Metadata
```

---

# 7. Document Ingestion Architecture

```text
Admin
  │
  ▼
PDF Upload
  │
  ▼
File Validation
  │
  ▼
Document Storage
  │
  ▼
PDF Text Extraction
  │
  ▼
Page-aware Text Cleaning
  │
  ▼
Chunking
  │
  ▼
Metadata Attachment
  │
  ▼
Embedding Generation
  │
  ▼
Vector Database
  │
  ▼
Processing Complete
```

---

# 8. Query Architecture

```text
User Question
     │
     ▼
Authentication
     │
     ▼
Conversation Context
     │
     ▼
Question Normalization
     │
     ▼
Embedding Generation
     │
     ▼
Vector Search
     │
     ▼
Top-K Results
     │
     ▼
Relevance Filtering
     │
     ├─────────────── No sufficient evidence
     │                         │
     │                         ▼
     │                 Unknown Response
     │
     ▼
Context Construction
     │
     ▼
LLM
     │
     ▼
Grounded Answer
     │
     ▼
Source Mapping
     │
     ▼
Database Storage
     │
     ▼
API Response
```

---

# 9. Technology Stack

## 9.1 Frontend

* React
* Vite
* Tailwind CSS
* React Router
* Axios

## 9.2 Backend

* Python 3.11+
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic
* PyJWT
* Passlib/bcrypt-compatible password hashing

## 9.3 RAG

* Sentence Transformers
* ChromaDB
* Configurable LLM provider

## 9.4 PDF Processing

Use a reliable PDF extraction library capable of page-level extraction.

Recommended:

* PyMuPDF

## 9.5 Database

* PostgreSQL

## 9.6 Testing

Backend:

* pytest
* pytest-asyncio
* HTTPX

Frontend:

* Vitest
* React Testing Library

## 9.7 Development

* Git
* Docker
* Docker Compose
* `.env`

---

# 10. Repository Structure

```text
college-rag-assistant/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   ├── router.py
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── chat.py
│   │   │       ├── conversations.py
│   │   │       ├── documents.py
│   │   │       └── admin.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── logging.py
│   │   │
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── models/
│   │   │       ├── user.py
│   │   │       ├── document.py
│   │   │       ├── conversation.py
│   │   │       └── message.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   ├── chat.py
│   │   │   ├── conversation.py
│   │   │   └── document.py
│   │   │
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── document_service.py
│   │   │   └── conversation_service.py
│   │   │
│   │   ├── rag/
│   │   │   ├── ingestion/
│   │   │   │   ├── loader.py
│   │   │   │   ├── cleaner.py
│   │   │   │   └── chunker.py
│   │   │   │
│   │   │   ├── embeddings/
│   │   │   │   └── embedder.py
│   │   │   │
│   │   │   ├── vectorstore/
│   │   │   │   └── chroma.py
│   │   │   │
│   │   │   ├── retrieval/
│   │   │   │   └── retriever.py
│   │   │   │
│   │   │   ├── generation/
│   │   │   │   ├── llm.py
│   │   │   └── prompt.py
│   │   │
│   │   └── main.py
│   │
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   │
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   ├── layout/
│   │   │   ├── documents/
│   │   │   └── common/
│   │   │
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Register.jsx
│   │   │   ├── Chat.jsx
│   │   │   ├── Conversations.jsx
│   │   │   ├── AdminDashboard.jsx
│   │   │   └── Documents.jsx
│   │   │
│   │   ├── services/
│   │   │   └── api.js
│   │   │
│   │   ├── hooks/
│   │   ├── contexts/
│   │   ├── routes/
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── package.json
│   └── Dockerfile
│
├── data/
│   ├── uploads/
│   └── chroma/
│
├── tests/
│   └── evaluation/
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── evaluation.md
│
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
└── SPEC.md
```

---

# 11. Environment Configuration

Create `.env.example`.

Required variables:

```env
APP_ENV=development
APP_NAME=College RAG Assistant

DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/college_rag

JWT_SECRET_KEY=change_this_in_production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

UPLOAD_DIR=./data/uploads

CHROMA_PERSIST_DIRECTORY=./data/chroma
CHROMA_COLLECTION_NAME=college_documents

EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

LLM_PROVIDER=gemini
LLM_MODEL=CHANGE_ME
LLM_API_KEY=CHANGE_ME

TOP_K=5
MIN_RELEVANCE_SCORE=CHANGE_ME

MAX_FILE_SIZE_MB=20
ALLOWED_FILE_TYPES=application/pdf
```

Never commit `.env`.

---

# 12. Authentication Specification

## Registration

Endpoint:

```http
POST /api/v1/auth/register
```

Request:

```json
{
  "name": "Student Name",
  "email": "student@example.com",
  "password": "secure-password"
}
```

Response:

```json
{
  "id": "uuid",
  "name": "Student Name",
  "email": "student@example.com",
  "role": "student"
}
```

Passwords MUST never be stored in plaintext.

---

# 13. Login

Endpoint:

```http
POST /api/v1/auth/login
```

Request:

```json
{
  "email": "student@example.com",
  "password": "secure-password"
}
```

Response:

```json
{
  "access_token": "JWT",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "name": "Student Name",
    "email": "student@example.com",
    "role": "student"
  }
}
```

---

# 14. User Database Model

Table: `users`

Fields:

```text
id              UUID PRIMARY KEY
name            VARCHAR(100)
email           VARCHAR(255) UNIQUE
password_hash   TEXT
role            ENUM(student, admin)
is_active       BOOLEAN
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

---

# 15. Document Model

Table: `documents`

Fields:

```text
id
title
filename
document_type
department
academic_year
semester
version
description
status
file_path
uploaded_by
created_at
updated_at
```

Status values:

```text
uploaded
processing
completed
failed
deleted
```

---

# 16. Document Upload API

Endpoint:

```http
POST /api/v1/documents
```

Authorization:

```text
Admin only
```

Multipart form:

```text
file
title
document_type
department
academic_year
semester
version
description
```

Maximum file size:

```text
20 MB
```

Allowed type:

```text
application/pdf
```

The backend must validate both:

* MIME type
* File signature/content

Do not trust the filename extension alone.

---

# 17. Document Processing

Document processing should run independently from the upload request where practical.

Initial implementation may process synchronously for simplicity.

Production implementation should use a background job.

Pipeline:

```text
Upload
  ↓
Validate
  ↓
Store Original
  ↓
Create Document DB Record
  ↓
Extract Text
  ↓
Chunk
  ↓
Generate Embeddings
  ↓
Insert Vectors
  ↓
Mark COMPLETED
```

If any stage fails:

```text
status = failed
```

The failure must be logged.

---

# 18. PDF Extraction

Use page-level extraction.

For every page:

```python
{
    "page_number": 1,
    "text": "..."
}
```

Do not merge all pages into one string before chunking.

Page information is required for source citation.

---

# 19. Text Cleaning

Cleaning should:

* Remove excessive whitespace.
* Normalize line breaks.
* Preserve meaningful headings.
* Preserve paragraph boundaries.
* Preserve page numbers.
* Avoid deleting meaningful numerical information.
* Avoid aggressive normalization.

Never perform destructive cleaning that changes the meaning of regulations, dates, fees, percentages, or course codes.

---

# 20. Chunking Specification

Initial parameters:

```text
chunk_size = approximately 500–800 tokens
chunk_overlap = approximately 50–100 tokens
```

These values are configuration parameters, not permanent constants.

Chunking should prefer:

1. Section boundaries
2. Paragraph boundaries
3. Sentence boundaries
4. Token-length limits

Each chunk must contain metadata:

```json
{
  "document_id": "uuid",
  "chunk_id": "uuid",
  "document_name": "Academic Regulations 2026.pdf",
  "page_number": 18,
  "section": "Attendance",
  "department": "General",
  "academic_year": "2026",
  "semester": null
}
```

---

# 21. Embedding Specification

The embedding model must be loaded once and reused.

Do not initialize the model for every request.

Required interface:

```python
class EmbeddingProvider:
    def embed_documents(self, texts):
        ...

    def embed_query(self, text):
        ...
```

This abstraction allows the model to be replaced later.

---

# 22. Vector Database Specification

The vector store must support:

* Insert
* Query
* Delete
* Metadata filtering
* Collection management

Every vector must be linked to a database document/chunk.

The application must never rely exclusively on vector database records as the authoritative document metadata store.

PostgreSQL is the authoritative relational database.

---

# 23. Retrieval Specification

Initial retrieval:

```text
top_k = 5
```

Process:

```text
Question
 ↓
Query embedding
 ↓
Vector similarity search
 ↓
Top 5 chunks
 ↓
Relevance filtering
```

The similarity metric and returned score must be normalized/documented appropriately.

Do NOT call the similarity score "confidence".

Use terminology such as:

* similarity score
* relevance score

---

# 24. Relevance Threshold

The system must have a configurable minimum retrieval relevance threshold.

Example:

```env
MIN_RELEVANCE_SCORE=...
```

The value must be determined experimentally.

Do NOT arbitrarily claim that a particular score means "correct".

If no retrieved chunk satisfies the threshold:

```text
answer_mode = unknown
```

---

# 25. RAG Prompt Specification

The generation prompt must enforce:

```text
You are a college information assistant.

Answer the user's question using only the supplied
retrieved context.

Rules:

1. Do not invent information.
2. Do not use unsupported college-specific facts.
3. Do not fabricate dates, fees, policies, regulations,
   requirements, or schedules.
4. If the context does not contain enough information,
   state that the information could not be found.
5. Keep the answer concise and directly relevant.
6. Use source references provided in the context.
```

The actual prompt may evolve during evaluation.

---

# 26. Context Format

The LLM should receive context in a structured format.

Example:

```text
SOURCE 1
Document: Academic Regulations 2026
Page: 18
Section: Attendance

[chunk text]


SOURCE 2
Document: Student Handbook 2026
Page: 32
Section: Examination Eligibility

[chunk text]
```

---

# 27. LLM Response Contract

The generation layer should return a structured internal result:

```json
{
  "answer": "Students must satisfy the attendance requirement...",
  "source_chunk_ids": [
    "chunk-uuid-1",
    "chunk-uuid-2"
  ],
  "answer_mode": "grounded"
}
```

Possible `answer_mode` values:

```text
grounded
unknown
error
```

The backend maps source chunk IDs to user-visible source metadata.

---

# 28. Unknown Answer Behavior

When insufficient evidence exists:

```json
{
  "answer": "I couldn't find reliable information about this in the college knowledge base.",
  "sources": [],
  "answer_mode": "unknown"
}
```

The LLM must not be allowed to fill the gap using general knowledge.

---

# 29. Chat API

Endpoint:

```http
POST /api/v1/chat
```

Request:

```json
{
  "conversation_id": "uuid-or-null",
  "message": "What is the minimum attendance requirement?"
}
```

Response:

```json
{
  "conversation_id": "uuid",
  "message": {
    "id": "uuid",
    "role": "assistant",
    "content": "Students must maintain...",
    "answer_mode": "grounded",
    "sources": [
      {
        "document_id": "uuid",
        "document_name": "Academic Regulations 2026.pdf",
        "page_number": 18,
        "section": "Attendance",
        "relevance_score": 0.87
      }
    ],
    "created_at": "timestamp"
  }
}
```

---

# 30. Conversation Model

Table: `conversations`

```text
id
user_id
title
created_at
updated_at
```

Only the owner or an authorized administrator may access a conversation.

---

# 31. Message Model

Table: `messages`

```text
id
conversation_id
role
content
answer_mode
created_at
```

Roles:

```text
user
assistant
```

Do not store API keys or sensitive system information in messages.

---

# 32. Message Sources

Table:

```text
message_sources
```

Fields:

```text
id
message_id
document_id
chunk_id
relevance_score
rank
created_at
```

This allows source information to remain traceable.

---

# 33. Conversation Context

For follow-up questions:

```text
Previous Conversation
        ↓
Question Resolution
        ↓
Retrieval Query
        ↓
RAG
```

Do not blindly send the entire conversation history to the LLM.

Use a configurable message history limit.

Initial recommendation:

```text
last 6–10 messages
```

The retrieved documents remain the factual grounding layer.

---

# 34. Admin Document API

## List

```http
GET /api/v1/documents
```

Admin only.

## Get

```http
GET /api/v1/documents/{document_id}
```

## Delete

```http
DELETE /api/v1/documents/{document_id}
```

Delete operation must:

1. Delete vector entries.
2. Delete chunks.
3. Delete document metadata.
4. Handle original file according to storage policy.

If vector deletion fails, the system must not silently report successful deletion.

---

# 35. Admin Dashboard MVP

Display:

```text
Total Documents
Completed Documents
Processing Documents
Failed Documents
Total Users
Total Conversations
Total Questions
```

Do not build advanced charts until the underlying metrics are correct.

---

# 36. Frontend Routes

Public:

```text
/login
/register
```

Student:

```text
/chat
/conversations
```

Admin:

```text
/admin
/admin/documents
```

Protected routes must check authentication state.

Admin routes must additionally verify role.

---

# 37. Chat UI Requirements

The chat page must include:

* Conversation sidebar
* New conversation button
* Message list
* User message
* Assistant message
* Loading state
* Error state
* Input box
* Send button
* Source list
* Source metadata
* Empty state

The UI must clearly distinguish:

```text
Grounded answer
```

from:

```text
Information unavailable
```

---

# 38. API Error Contract

All API errors should use a consistent format.

Example:

```json
{
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "The requested document was not found."
  }
}
```

Common error codes:

```text
INVALID_CREDENTIALS
UNAUTHORIZED
FORBIDDEN
DOCUMENT_NOT_FOUND
INVALID_FILE
FILE_TOO_LARGE
DOCUMENT_PROCESSING_FAILED
LLM_ERROR
VECTOR_STORE_ERROR
VALIDATION_ERROR
INTERNAL_ERROR
```

Do not expose internal stack traces to clients.

---

# 39. Logging

Backend logs should include:

* Request ID
* Endpoint
* User ID where appropriate
* Document ID where appropriate
* Processing status
* Retrieval duration
* LLM duration
* Error information

Never log:

* Passwords
* JWT secrets
* API keys
* Full sensitive authentication tokens

---

# 40. Testing Strategy

Testing is mandatory.

## Unit Tests

Test:

* Password hashing
* JWT creation/validation
* PDF extraction
* Text cleaning
* Chunking
* Metadata creation
* Embedding interface
* Retrieval
* Relevance filtering
* Prompt construction

## Integration Tests

Test:

```text
Register
 ↓
Login
 ↓
Upload Document
 ↓
Process Document
 ↓
Ask Question
 ↓
Retrieve Context
 ↓
Generate Answer
 ↓
Return Sources
```

---

# 41. RAG Evaluation Dataset

Create:

```text
tests/evaluation/questions.json
```

Structure:

```json
[
  {
    "question": "What is the minimum attendance requirement?",
    "expected_document": "Academic Regulations 2026",
    "expected_pages": [18],
    "expected_keywords": [
      "attendance"
    ]
  }
]
```

The dataset must contain:

* Easy questions
* Paraphrased questions
* Exact keyword questions
* Multi-turn questions
* Unanswerable questions
* Ambiguous questions

---

# 42. Retrieval Evaluation

Implement:

* Recall@1
* Recall@3
* Recall@5
* MRR
* Hit Rate

Example:

```text
Question
 ↓
Retrieve Top-K
 ↓
Compare retrieved chunk/document
with expected answer source
```

Evaluation results must be reproducible.

---

# 43. Answer Evaluation

Evaluate:

### Faithfulness

Is the generated answer supported by retrieved context?

### Relevance

Does the answer answer the question?

### Citation correctness

Does the cited source actually support the answer?

### Unknown handling

Does the system correctly refuse unsupported questions?

---

# 44. Security Requirements

Mandatory:

* Password hashing
* JWT validation
* Role-based authorization
* Input validation
* File type validation
* File size limits
* API key protection
* CORS configuration
* Secure environment variables

Never put:

```text
LLM_API_KEY
JWT_SECRET_KEY
DATABASE_PASSWORD
```

in frontend code.

---

# 45. File Storage

MVP:

```text
data/uploads/
```

Production:

Use object storage.

The database stores the file reference rather than the entire PDF binary where practical.

---

# 46. Database Migrations

Use Alembic.

Never manually modify production database schemas.

Workflow:

```text
Modify SQLAlchemy model
        ↓
Generate migration
        ↓
Review migration
        ↓
Apply migration
```

---

# 47. Docker Development Environment

`docker-compose.yml` should provide:

```text
frontend
backend
postgres
```

Chroma may initially use a persistent local volume.

The system should be startable using:

```bash
docker compose up
```

---

# 48. Environment Separation

Support:

```text
development
testing
production
```

Configuration must come from environment variables.

Never hard-code production credentials.

---

# 49. API Documentation

FastAPI's automatic documentation must remain enabled during development.

Required:

```text
/docs
/redoc
```

Every API endpoint must have:

* Description
* Request schema
* Response schema
* Error responses
* Authentication requirement

---

# 50. Development Order

Implementation MUST follow this order.

## Step 1 — Repository

Create:

```text
backend/
frontend/
data/
docs/
tests/
```

## Step 2 — Backend Foundation

Implement:

* FastAPI
* Configuration
* PostgreSQL
* SQLAlchemy
* Alembic
* Logging

## Step 3 — Authentication

Implement:

* User model
* Registration
* Login
* JWT
* Role checking

## Step 4 — Document Management

Implement:

* Upload
* Validation
* Storage
* Metadata
* Admin authorization

## Step 5 — Ingestion Pipeline

Implement:

```text
PDF
 ↓
Extraction
 ↓
Cleaning
 ↓
Chunking
 ↓
Metadata
```

Test this independently before adding embeddings.

## Step 6 — Embeddings

Implement:

```text
Chunk
 ↓
Embedding
```

Test embedding generation independently.

## Step 7 — Vector Database

Implement:

* Collection
* Insert
* Search
* Delete

Test retrieval independently.

## Step 8 — Basic RAG

Implement:

```text
Question
 ↓
Embedding
 ↓
Search
 ↓
Top-K
 ↓
Context
 ↓
LLM
```

## Step 9 — Source Mapping

Connect retrieved chunks to:

* Document
* Page
* Section

## Step 10 — Chat

Implement:

* Conversations
* Messages
* Context
* Sources

## Step 11 — Frontend

Implement:

* Login
* Register
* Chat
* History
* Admin documents

## Step 12 — Testing

Run:

```text
Unit tests
Integration tests
RAG evaluation
```

## Step 13 — Advanced Retrieval

Only after MVP works:

```text
Keyword search
+
Semantic search
↓
Hybrid retrieval
↓
Reranking
```

## Step 14 — Deployment

Deploy only after the local system passes the acceptance criteria.

---

# 51. Definition of Done — MVP

The MVP is complete only when:

* [ ] A user can register.
* [ ] A user can log in.
* [ ] Admin authentication works.
* [ ] Admin can upload a PDF.
* [ ] PDF text is extracted.
* [ ] Text is chunked.
* [ ] Embeddings are generated.
* [ ] Chunks are stored in vector DB.
* [ ] Student can ask a question.
* [ ] Relevant chunks are retrieved.
* [ ] LLM receives retrieved context.
* [ ] Answer is generated.
* [ ] Sources are displayed.
* [ ] Unsupported questions are rejected.
* [ ] Conversations are stored.
* [ ] Users can view their conversations.
* [ ] Admin can delete documents.
* [ ] Vector entries are deleted with documents.
* [ ] API errors are handled.
* [ ] Authentication is enforced server-side.
* [ ] Automated tests pass.
* [ ] Application runs locally from documented instructions.
* [ ] Application is deployed.

---

# 52. Definition of Done — Advanced Version

Advanced completion requires:

* [ ] Hybrid retrieval
* [ ] Metadata filtering
* [ ] Reranking
* [ ] Document versioning
* [ ] Feedback
* [ ] Source preview
* [ ] Analytics
* [ ] Evaluation dataset
* [ ] Recall@K
* [ ] MRR
* [ ] Hit Rate
* [ ] Faithfulness evaluation
* [ ] Citation evaluation
* [ ] Hallucination analysis

---

# 53. Performance Targets

These are engineering targets, not guaranteed values.

For a small college knowledge base:

```text
API response overhead: < 500 ms excluding LLM
Retrieval: < 500 ms target
Document ingestion: asynchronous where possible
```

End-to-end response time will depend heavily on the selected LLM provider.

Performance must be measured rather than assumed.

---

# 54. RAG Quality Targets

Before production deployment, establish a baseline evaluation.

Recommended initial target:

```text
Recall@5: >= 0.80
```

Then improve experimentally.

Do not manipulate the evaluation dataset to achieve the target.

The evaluation dataset must remain separate from development tuning data.

---

# 55. Observability

At minimum record:

```text
question
retrieved_chunk_ids
retrieval_scores
retrieval_latency
answer_mode
response_latency
source_documents
feedback
```

This allows future debugging of:

> Why did the chatbot give this answer?

---

# 56. Important Engineering Rules

## Rule 1

Never fabricate source citations.

## Rule 2

Never claim that a similarity score is an answer confidence percentage.

## Rule 3

Never allow students to modify the knowledge base.

## Rule 4

Never expose API keys in the frontend.

## Rule 5

Never rely exclusively on the LLM for college-specific facts.

## Rule 6

Never optimize UI before validating retrieval quality.

## Rule 7

Never add advanced RAG components before establishing a measurable baseline.

## Rule 8

Every retrieved source must be traceable to an actual document chunk.

## Rule 9

Every document chunk must retain page-level metadata.

## Rule 10

Unknown questions must be treated as a valid system outcome, not as an error.

---

# 57. Research Extension

Once the production MVP is working, the project can become an experimental RAG study.

Primary research question:

> How do retrieval strategy and reranking affect the factual reliability of a college-domain RAG system?

Experiments:

```text
Experiment A
Vector Search

Experiment B
Hybrid Search

Experiment C
Hybrid Search + Reranking
```

Measure:

```text
Recall@K
MRR
Hit Rate
Faithfulness
Answer Relevance
Citation Correctness
Unknown-question accuracy
Latency
```

The results should be recorded and analyzed rather than assumed.

---

# 58. Future Architecture

The system should eventually support:

```text
                    Query
                      │
                      ▼
               Query Classifier
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       General     Department   Document
       Knowledge   Knowledge    Specific
          │           │           │
          └───────────┼───────────┘
                      ▼
               Hybrid Retrieval
                      │
                      ▼
                  Reranker
                      │
                      ▼
               Context Builder
                      │
                      ▼
                     LLM
                      │
              ┌───────┴───────┐
              ▼               ▼
           Answer          Evidence
```

This architecture is NOT part of the MVP.

---

# 59. Project Success Definition

The project succeeds if a student can ask a natural-language college question and receive:

1. A useful answer.
2. An answer grounded in institutional documents.
3. A traceable source.
4. A page/section reference where available.
5. An honest unknown response when evidence is unavailable.

The project should demonstrate:

> **Retrieval quality + grounded generation + source transparency + measurable evaluation.**

---

# 60. Final Implementation Principle

Build the system in this order:

```text
WORKING
   ↓
CORRECT
   ↓
MEASURABLE
   ↓
OPTIMIZED
   ↓
POLISHED
```

Do not reverse this order.

The first milestone is not a beautiful chatbot.

The first milestone is:

```text
PDF
 ↓
Extract
 ↓
Chunk
 ↓
Embed
 ↓
Vector DB
 ↓
Retrieve
 ↓
LLM
 ↓
Grounded Answer
 ↓
Source
```

Once this pipeline works reliably, build the rest of the application around it.
