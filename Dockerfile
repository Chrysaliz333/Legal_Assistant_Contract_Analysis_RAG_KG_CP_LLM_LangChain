# Multi-stage Dockerfile for Legal Assistant Multi-Session Continuity System
# Python 3.10.11 base

FROM python:3.10.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# Development stage
# ============================================================================
FROM base as development

# Copy requirements
COPY requirements-new.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-new.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p storage logs chroma_db

# Expose port
EXPOSE 8000

# Development command (with auto-reload)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================================================
# Production stage
# ============================================================================
FROM base as production

# Copy requirements
COPY requirements-new.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-new.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p storage logs chroma_db

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command (with workers)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
