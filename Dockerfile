# Multi-stage Docker build: Python builder → Node builder → Runtime

# Stage 1: Python dependencies
FROM python:3.14-slim-bookworm AS python-builder

WORKDIR /app

# Copy dependency manifests (README.md is required by pyproject.toml's
# hatchling build backend, which reads it as the package long description).
COPY pyproject.toml uv.lock* README.md ./

# Install uv and sync dependencies
RUN pip install --no-cache-dir uv && \
    uv sync --no-dev

# Stage 2: Node/SvelteKit build
FROM node:26-bookworm-slim AS node-builder

WORKDIR /ui

# Copy package files
COPY ui/package.json ui/pnpm-lock.yaml ./

# Install pnpm (version pinned via package.json's "packageManager" field).
# Corepack is no longer bundled with Node.js as of Node 25+, so it must be
# installed explicitly before it can be enabled.
RUN npm install -g corepack@latest && \
    corepack enable && \
    pnpm install --frozen-lockfile

# Copy source and build
COPY ui/ .
RUN pnpm build

# Stage 3: Runtime
FROM python:3.14-slim-bookworm

# Install runtime dependencies: nginx, curl (for health check), gettext-base
# (provides envsubst, used by entrypoint.sh for $PORT substitution)
RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx curl gettext-base && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy Python virtual environment from builder
COPY --from=python-builder /app/.venv /app/.venv

# Copy compiled UI from builder (adapter-static writes to ui/build, see
# ui/svelte.config.js)
COPY --from=node-builder /ui/build /var/www/html

# Copy application code
COPY api/ /app/api/
COPY searches.yaml /app/

# Copy nginx and startup scripts
COPY scripts/nginx.conf.template /etc/nginx/nginx.conf.template
COPY scripts/entrypoint.sh /app/entrypoint.sh

# Make entrypoint executable and fix permissions. nginx's pidfile lives
# under /tmp/nginx (created by entrypoint.sh at startup), not /var/run,
# since /var/run isn't writable by a non-root user on this base image.
# /var/lib/nginx must also be writable - nginx creates its client_body/proxy
# temp directories under there on first use.
RUN chmod +x /app/entrypoint.sh && \
    chown -R appuser:appuser /app /var/www /var/log/nginx /var/lib/nginx

# Switch to non-root user
USER appuser

# Expose port (will be overridden by $PORT env var at startup)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/api/health || exit 1

# Start application
ENTRYPOINT ["/app/entrypoint.sh"]
