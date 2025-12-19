# =============================================================================
# Backend Dockerfile for Data Agent V4
# Multi-stage build with development and production support
# =============================================================================

FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        curl \
        build-essential \
        git \
        wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base AS development
ENV ENVIRONMENT development
ENV DEBUG true

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

# Copy project with development support
COPY --chown=app:app . .

# Create necessary directories
RUN mkdir -p /app/uploads /app/logs /app/temp \
    && chown -R app:app /app/uploads /app/logs /app/temp

USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Development command with hot reload
# 🔥 Token Expansion: 增加 --timeout-keep-alive 到 300 秒以支持长文本生成
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug", "--timeout-keep-alive", "300"]

# Production stage
FROM base AS production
ENV ENVIRONMENT production
ENV DEBUG false

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

# Copy project
COPY --chown=app:app . .

# Create necessary directories
RUN mkdir -p /app/uploads /app/logs /app/temp \
    && chown -R app:app /app/uploads /app/logs /app/temp

USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command
# 🔥 Token Expansion: 增加 --timeout-keep-alive 到 300 秒以支持长文本生成
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--timeout-keep-alive", "300"]