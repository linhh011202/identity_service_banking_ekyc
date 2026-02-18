# ------------------------------------------------------------------
# Stage 1 – Build dependencies with uv
# ------------------------------------------------------------------
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy source code and install the project itself
COPY . .
RUN uv sync --frozen --no-dev

# ------------------------------------------------------------------
# Stage 2 – Minimal runtime image
# ------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Install runtime system dependencies for psycopg2-binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app ./app

# Config is mounted at runtime via Cloud Run secret volume
# Local dev: docker run -v $(pwd)/config.yaml:/app/secrets/config.yaml ...
ENV CONFIG_PATH="/app/secrets/config.yaml"
ENV PATH="/app/.venv/bin:$PATH"

# Cloud Run injects PORT env var (default 8080)
ENV PORT=8080

EXPOSE ${PORT}

CMD ["sh", "-c", "fastapi run ./app/main.py --host 0.0.0.0 --port ${PORT}"]
