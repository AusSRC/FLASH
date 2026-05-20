# =========================================================
# Builder
# =========================================================

FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

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

# Install only dependencies first
RUN uv sync --frozen --no-dev --no-install-project

# ---------------------------------------------------------
# Copy source code
# ---------------------------------------------------------

COPY . .

# Install local project into virtualenv
RUN uv sync --frozen --no-dev

# =========================================================
# Runtime
# =========================================================

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# ---------------------------------------------------------
# Create non-root user
# ---------------------------------------------------------

RUN groupadd --system app && \
    useradd --system --gid app --create-home app

# ---------------------------------------------------------
# Copy application
# ---------------------------------------------------------

COPY --from=builder /app /app

# ---------------------------------------------------------
# Set ownership
# ---------------------------------------------------------

RUN chown -R app:app /app

# ---------------------------------------------------------
# Switch to non-root user
# ---------------------------------------------------------

USER app

# ---------------------------------------------------------
# Start Gunicorn
# ---------------------------------------------------------

CMD ["gunicorn", "flashdb.wsgi:application", "--bind", "0.0.0.0:8000"]