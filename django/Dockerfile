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
RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "flashdb.wsgi:application", "--bind", "0.0.0.0:8000"]