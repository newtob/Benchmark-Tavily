set shell := ["bash", "-uc"]

## Typical flow: just otel-up → use Claude Code → just otel-parse → just otel-costs → just otel-down.
## App flow: just install → just docker-build → just docker-run → open http://localhost:8080

# List all
default:
    @just --list

# Install both Python and TypeScript toolchains
[group('all')]
install:
    uv sync --group dev
    pnpm install

# Run the full local quality gate (prek: format, lint, typecheck, secrets)
[group('all')]
check:
    prek run --all-files

# Everything CI runs: check + both test suites
[group('all')]
ci: check py-test ts-test

# --- Python -------------------------------------------------------------

[group('py')]
py-lint:
    uv run ruff check .

[group('py')]
py-format:
    uv run ruff format .

[group('py')]
py-typecheck:
    uv run mypy api otel tests scripts

[group('py')]
py-test:
    uv run pytest

# --- TypeScript / Svelte --------------------------------------------------

[group('ts')]
ts-lint:
    pnpm run lint

[group('ts')]
ts-format:
    pnpm run format

[group('ts')]
ts-typecheck:
    bash ./scripts/hooks/ts-typecheck.sh

[group('ts')]
ts-test:
    pnpm run test

# --- OTel per-prompt cost -------------------------------------------------

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

# Join prompt costs against the logged prompt text/summary (by prompt_id)
[group('otel')]
otel-report:
    python3 otel/join_prompt_journal.py

# Delete captured telemetry output (logs, metrics, parsed costs, journal)
[group('otel')]
otel-clean:
    rm -f otel/output/otel-logs.jsonl otel/output/otel-metrics.jsonl otel/output/prompt_costs.json otel/output/prompt_journal.jsonl otel/output/prompt_report.json

# --- Tavily Benchmark app -------------------------------------------------

# Record fresh benchmark fixtures (needs TAVILY_API_KEY + `claude /login`)
[group('app')]
record-fixtures:
    uv run python3 scripts/record_benchmark_fixtures.py

# Build the app's Docker image
[group('app')]
docker-build:
    docker build -t tavily-benchmark:local .

# Run the app's Docker image, publishing :8080
[group('app')]
docker-run:
    docker run --rm -d --name tavily-benchmark -p 8080:8080 tavily-benchmark:local

# Stop the running app container
[group('app')]
docker-stop:
    docker stop tavily-benchmark

# Build, run, and poll /api/healthz then / — a fast sanity loop before Playwright
[group('app')]
docker-check: docker-build docker-run
    #!/usr/bin/env bash
    set -euo pipefail
    for _ in $(seq 1 30); do
      if curl -sf -o /dev/null http://localhost:8080/api/healthz; then
        echo "healthy"
        curl -sf -o /dev/null http://localhost:8080/ && echo "root OK"
        exit 0
      fi
      sleep 1
    done
    echo "container did not become healthy in time" >&2
    exit 1

# Install Playwright's browser (one-time / CI setup)
[group('app')]
e2e-install:
    pnpm --dir e2e exec playwright install --with-deps chromium

# Run Playwright against an already-running container (PLAYWRIGHT_BASE_URL overridable)
[group('app')]
e2e:
    pnpm --dir e2e exec playwright test

# Build, run, test, and tear down — the recipe CI's PR workflow calls
[group('app')]
e2e-full:
    #!/usr/bin/env bash
    set -euo pipefail
    just docker-build
    just docker-run
    trap 'just docker-stop || true' EXIT
    for _ in $(seq 1 30); do
      curl -sf -o /dev/null http://localhost:8080/api/healthz && break
      sleep 1
    done
    just e2e
