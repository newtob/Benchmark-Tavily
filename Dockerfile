# syntax=docker/dockerfile:1
# Multi-stage build: SvelteKit static build -> Python deps -> minimal
# runtime (nginx + uvicorn, one container). See specs/tavily-benchmark-app.md §8.

FROM node:22.23.2-bookworm-slim AS ui-build
WORKDIR /src
RUN corepack enable
COPY pnpm-workspace.yaml pnpm-lock.yaml .npmrc package.json ./
COPY apps/ui/package.json apps/ui/package.json
RUN pnpm install --frozen-lockfile --filter @tavily-benchmark/ui
COPY apps/ui apps/ui
RUN pnpm --filter @tavily-benchmark/ui run build

FROM python:3.15.2-slim-bookworm AS python-deps
WORKDIR /src
RUN pip install --no-cache-dir uv==0.12.13
COPY pyproject.toml uv.lock ./
RUN uv export --no-dev --no-hashes -o requirements.txt \
    && pip install --no-cache-dir --target /python-env -r requirements.txt

FROM python:3.15.2-slim-bookworm AS runtime
RUN apt-get update \
    && apt-get install --no-install-recommends -y nginx curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/static /run/nginx \
    && chown -R appuser:appuser /app /run/nginx /var/lib/nginx /var/log/nginx

WORKDIR /app
ENV PYTHONPATH=/python-env:/app \
    PATH=/python-env/bin:$PATH \
    PORT=8080

COPY --from=python-deps /python-env /python-env
COPY --from=ui-build /src/apps/ui/build /app/static
COPY api /app/api
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD curl -sf "http://localhost:${PORT}/api/healthz" || exit 1

USER appuser
ENTRYPOINT ["/app/entrypoint.sh"]
