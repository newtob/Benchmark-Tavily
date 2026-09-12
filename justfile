set shell := ["bash", "-uc"]

## Typical flow: just otel-up → use Claude Code → just otel-parse → just otel-costs → just otel-down.

# List available recipes
default:
    @just --list

# Install both Python and TypeScript toolchains
[group('all')]
install: py-sync ts-install

# Run the full local quality gate (same checks as CI's quality job)
[group('all')]
check:
    uv run prek run --all-files --config prek.toml

# Run everything CI runs: quality gate + both test suites
[group('all')]
ci: check py-test ts-test

# Sync Python dependencies (uv)
[group('py')]
py-sync:
    uv sync --group dev

# Lint Python source
[group('py')]
py-lint:
    uv run ruff check .

# Format Python source
[group('py')]
py-format:
    uv run ruff format .

# Type-check Python source (mypy, strict)
[group('py')]
py-typecheck:
    uv run mypy otel tests

# Run Python tests (pytest)
[group('py')]
py-test:
    uv run pytest

# Install TypeScript/Node dependencies (pnpm)
[group('ts')]
ts-install:
    pnpm install

# Lint TypeScript/JS source (Biome)
[group('ts')]
ts-lint:
    pnpm run lint

# Format TypeScript/JS source (Biome, writes fixes)
[group('ts')]
ts-format:
    pnpm run format

# Type-check TypeScript source (tsc); skips cleanly if no .ts files exist yet
[group('ts')]
ts-typecheck:
    pnpm run typecheck

# Run TypeScript tests (Vitest)
[group('ts')]
ts-test:
    pnpm run test

# Start the OTel collector (docker compose, detached)
[group('otel')]
otel-up:
    docker compose -f otel/docker-compose.yml up -d

# Stop and remove the OTel collector
[group('otel')]
otel-down:
    docker compose -f otel/docker-compose.yml down

# Restart the OTel collector
[group('otel')]
otel-restart: otel-down otel-up

# Show OTel collector container status
[group('otel')]
otel-status:
    docker compose -f otel/docker-compose.yml ps

# Follow the OTel collector's logs
[group('otel')]
otel-logs:
    docker compose -f otel/docker-compose.yml logs -f

# Validate the collector config without starting it
[group('otel')]
otel-check:
    docker compose -f otel/docker-compose.yml config -q

# Parse captured logs into per-prompt token/cost aggregates
[group('otel')]
otel-parse *ARGS:
    python3 otel/parse_prompt_costs.py {{ARGS}}

# Print the last parsed per-prompt cost summary
[group('otel')]
otel-costs:
    cat otel/output/prompt_costs.json

# Delete captured telemetry output (logs, metrics, parsed costs)
[group('otel')]
otel-clean:
    rm -f otel/output/otel-logs.jsonl otel/output/otel-metrics.jsonl otel/output/prompt_costs.json
