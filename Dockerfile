# syntax=docker/dockerfile:1.4
# Aegis-Eval Production Hardened Dockerfile
# Enforces non-root execution, minimal attack surface, and container immutability.

# --- Stage 1: Build & Dependencies ---
FROM python:3.11-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Install build essentials if needed for wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy locked dependencies
COPY requirements-frozen.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements-frozen.txt

# --- Stage 2: Hardened Runtime ---
FROM python:3.11-slim AS runtime

LABEL maintainer="Aegis Security Team <security@aegis-eval.example.com>"
LABEL org.opencontainers.image.title="Aegis-Eval Security Harness"
LABEL org.opencontainers.image.description="Hardened, Capability-Based Adversarial RAG Evaluation Runtime"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    AEGIS_ENV="production" \
    PORT=8000

# Create dedicated unprivileged system user and group (UID/GID 10001)
RUN groupadd -g 10001 aegis && \
    useradd -u 10001 -g aegis -s /sbin/nologin -M -d /app aegis

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder --chown=aegis:aegis /opt/venv /opt/venv

# Copy application source code with unprivileged ownership
COPY --chown=aegis:aegis src/ /app/src/
COPY --chown=aegis:aegis pyproject.toml /app/
COPY --chown=aegis:aegis scripts/ /app/scripts/

# Ensure runtime directories exist with restricted permissions
RUN mkdir -p /app/reports /tmp && \
    chown -R aegis:aegis /app/reports /tmp && \
    chmod 700 /app/reports /tmp

# Switch to unprivileged non-root user
USER 10001:10001

EXPOSE 8000

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

ENTRYPOINT ["python", "-m", "uvicorn", "src.aegis_eval.v4.api:app", "--host", "0.0.0.0", "--port", "8000"]
