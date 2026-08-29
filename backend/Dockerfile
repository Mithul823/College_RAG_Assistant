# Multi-stage Python 3.12 Dockerfile for College RAG Assistant Backend
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files, enable unbuffered output & restrict thread pools for Render 512MB RAM cap
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    TORCH_NUM_THREADS=1

WORKDIR /app

# Install system runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ ./app/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Create persistent storage directories
RUN mkdir -p data/uploads data/chroma

# Render dynamically assigns PORT environment variable
EXPOSE 8000

# Launch application with Uvicorn dynamically binding to Render's $PORT (defaults to 8000)
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
