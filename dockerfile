# ============================================
# Knowledge Base RAG Backend - Production Dockerfile
# Compatible with Python 3.12 and 3.13
# ============================================

# Build stage for dependencies
FROM python:3.12-slim-bookworm AS builder

# Set build environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libmagic1 \
    libmagic-dev \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    libpoppler-cpp-dev \
    pkg-config \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt

# Install PageIndex from GitHub
RUN pip install git+https://github.com/VectifyAI/PageIndex.git

# ============================================
# Production stage
# ============================================
FROM python:3.12-slim-bookworm AS production

# Labels for metadata
LABEL maintainer="Knowledge Base Team" \
      version="1.0.0" \
      description="Production-ready Knowledge Base RAG Backend"

# Set production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PATH="/opt/venv/bin:$PATH" \
    APP_HOME=/app \
    # Application settings
    APP_ENV=production \
    LOG_LEVEL=INFO \
    WORKERS=4 \
    HOST=0.0.0.0 \
    PORT=8000

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /tmp/* /var/tmp/*

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Create application directories
RUN mkdir -p ${APP_HOME} \
    ${APP_HOME}/uploads \
    ${APP_HOME}/logs \
    ${APP_HOME}/data \
    ${APP_HOME}/cache \
    && chown -R appuser:appgroup ${APP_HOME}

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR ${APP_HOME}

# Copy application code
COPY --chown=appuser:appgroup ./app/ ${APP_HOME}/app/

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - production with gunicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop", "--http", "httptools"]

# ============================================
# Development stage (optional)
# ============================================
FROM production AS development

# Switch to root temporarily for dev dependencies
USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    isort \
    mypy \
    flake8

# Switch back to non-root user
USER appuser

# Override command for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]