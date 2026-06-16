# =========================================================
# Builder
# =========================================================

FROM python:3.10.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app
# ---------------------------------------------------------
# System build dependencies
# ---------------------------------------------------------

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# Install uv
# ---------------------------------------------------------

RUN pip install --no-cache-dir uv --root-user-action=ignore

# ---------------------------------------------------------
# Dependency layer (cache-friendly)
# ---------------------------------------------------------

COPY pyproject.toml uv.lock ./

# ---------------------------------------------------------
# Copy source code
# ---------------------------------------------------------

COPY flashdb .

# Install local project into virtualenv
RUN uv sync --frozen --no-dev

# =========================================================
# Runtime
# =========================================================

FROM python:3.10.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# ---------------------------------------------------------
# Create non-root user thats forced to UID 999 and Group flash which
# exists on the VM as flash with gui 2000
# ---------------------------------------------------------

RUN groupadd -g 2000 flash && \
    useradd -m -u 999 -g flash app

# ---------------------------------------------------------
# Copy application
# ---------------------------------------------------------

COPY --from=builder /app /app

# ---------------------------------------------------------
# Set ownership
# ---------------------------------------------------------

RUN chown -R app:flash /app


# ---------------------------------------------------------
# Start Gunicorn
# ---------------------------------------------------------
CMD ["gunicorn", "flashdb.wsgi:application", "--bind", "0.0.0.0:8000"]