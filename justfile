#!/usr/bin/env just --justfile

set shell := ["bash", "-uc"]

# Resolve a pnpm invocation that works whether pnpm is on PATH, only
# reachable via corepack, or not installed at all (falls back to npx).
pnpm := `if command -v pnpm >/dev/null 2>&1; then echo pnpm; elif command -v corepack >/dev/null 2>&1; then corepack enable >/dev/null 2>&1; echo pnpm; else echo "npx --yes pnpm@9.15.0"; fi`

# Show all recipes
help:
    @just --list

# === API Tasks ===

[group('api')]
@api-sync:
    echo "📦 Syncing Python dependencies..."
    python -m uv sync --extra dev

[group('api')]
@api-fmt-check:
    echo "✓ Checking Python formatting..."
    python -m ruff format --check api/

[group('api')]
@api-fmt-fix:
    echo "🔄 Fixing Python formatting..."
    python -m ruff format api/
    python -m ruff check --fix api/

[group('api')]
@api-lint-check:
    echo "✓ Checking Python linting..."
    python -m ruff check api/

[group('api')]
@api-typecheck:
    echo "🔍 Type checking Python..."
    python -m mypy api/

[group('api')]
@api-test:
    echo "🧪 Running Python unit tests..."
    python -m pytest api/tests/ -v

[group('api')]
@api-test-watch:
    echo "👁️ Running tests in watch mode..."
    python -m pytest api/tests/ --tb=short -q --ff

# === UI Tasks ===

[group('ui')]
@ui-sync:
    echo "📦 Syncing Node dependencies..."
    cd ui && {{pnpm}} install

[group('ui')]
@ui-typecheck:
    echo "🔍 Type checking TypeScript..."
    cd ui && {{pnpm}} run type-check

[group('ui')]
@ui-lint-check:
    echo "✓ Checking TypeScript linting..."
    cd ui && {{pnpm}} exec biome check .

[group('ui')]
@ui-lint-fix:
    echo "🔄 Fixing TypeScript linting..."
    cd ui && {{pnpm}} exec biome check --fix .

[group('ui')]
@ui-dev:
    echo "🚀 Starting UI dev server..."
    cd ui && {{pnpm}} dev

[group('ui')]
@ui-build:
    echo "🔨 Building UI..."
    cd ui && {{pnpm}} build

[group('ui')]
@ui-test:
    echo "🧪 Running Playwright tests..."
    cd ui && {{pnpm}} exec playwright test

[group('ui')]
@ui-test-ui:
    echo "👁️ Running Playwright tests (UI mode)..."
    cd ui && {{pnpm}} exec playwright test --ui

# === Container Tasks ===

[group('container')]
@docker-build:
    echo "🐳 Building Docker image..."
    docker build -t benchmark-tavily:latest .
    echo "✅ Docker image built: benchmark-tavily:latest"

[group('container')]
@docker-run:
    echo "🚀 Running Docker container..."
    echo "👉 http://localhost:8080 (not 8000 - that port is internal-only)"
    if [ -f .env ]; then \
        docker run -p 8080:8080 --env-file .env -it benchmark-tavily:latest; \
    else \
        echo "⚠️  No .env found (cp .env.template .env to add TAVILY_API_KEY) - running without it"; \
        docker run -p 8080:8080 -it benchmark-tavily:latest; \
    fi

[group('container')]
@docker-stop:
    echo "🛑 Stopping all running containers..."
    if [ -n "$(docker ps -q)" ]; then \
        docker stop $(docker ps -q); \
        echo "✅ All containers stopped"; \
    else \
        echo "ℹ️  No running containers"; \
    fi

[group('container')]
@serve: docker-build docker-run
    @true

# === All Tasks ===

[group('dev')]
@sync: api-sync ui-sync
    echo "✅ All dependencies synced"

[group('dev')]
@fmt-fix: api-fmt-fix ui-lint-fix
    echo "✅ All formatting fixed"

[group('dev')]
@check:
    echo "🔍 Running full validation..."
    prek run --all-files
    echo "✅ All checks passed"

[group('dev')]
@test: api-test ui-test
    echo "✅ All tests passed"

[group('dev')]
@clean:
    echo "🧹 Cleaning up..."
    rm -rf api/__pycache__ api/.pytest_cache api/.mypy_cache
    rm -rf ui/node_modules ui/.svelte-kit ui/dist ui/build
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    echo "✅ Cleanup complete"

[group('dev')]
@ci: check test docker-build
    echo "✅ CI pipeline complete"
