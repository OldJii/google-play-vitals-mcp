# Multi-stage build for minimal runtime image
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md README_CN.md LICENSE CHANGELOG.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir build && \
    python -m build --wheel && \
    pip install --no-cache-dir dist/*.whl

# Final lightweight runner image
FROM python:3.12-slim AS runner

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/google-play-vitals-mcp /usr/local/bin/google-play-vitals-mcp

# Create non-root user
RUN useradd -m -u 1000 mcpuser
USER mcpuser

ENTRYPOINT ["google-play-vitals-mcp"]
CMD ["run"]
