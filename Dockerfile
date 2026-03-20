# =============================================================================
# Aegis Deploy — Dockerfile
# =============================================================================
# Multi-stage build for the MAP container.
# Base: NVIDIA PyTorch for GPU + CUDA support.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — install dependencies
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# System dependencies for psycopg2, pydicom, pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Install aegis core library
RUN pip install --no-cache-dir --prefix=/install \
    "monai-aegis @ git+https://github.com/lakshmi-mahabaleshwara/aegis.git#subdirectory=monai_aegis"

# Copy and install aegis-deploy
COPY pyproject.toml ./
COPY aegis_deploy/ ./aegis_deploy/
RUN pip install --no-cache-dir --prefix=/install .

# ---------------------------------------------------------------------------
# Stage 2: Runtime — lean production image
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY aegis_deploy/ ./aegis_deploy/

# Create data directories
RUN mkdir -p /data/input /data/output /data/not_processed /tmp/manifests

# Non-root user for security
RUN groupadd -r aegis && useradd -r -g aegis -s /sbin/nologin aegis
RUN chown -R aegis:aegis /app /data /tmp/manifests
USER aegis

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import aegis_deploy; print('ok')" || exit 1

# Default entry point
ENTRYPOINT ["aegis-deploy"]
CMD ["--help"]

# Labels
LABEL maintainer="Aegis Team" \
      description="Aegis Deploy — Medical Image De-Identification MAP" \
      version="0.1.0"
