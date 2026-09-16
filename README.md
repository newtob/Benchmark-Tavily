# Benchmark-Tavily

A benchmarking application that measures the cost and token efficiency of web search tools when used with Claude Sonnet 5 and other Anthropic models.

## Overview

This app compares three methods of delivering search results to Claude:

1. **Tavily CLI** — Search via CLI, manually pass results to Claude API in prompt
2. **Tavily MCP** — Integrated MCP search within Claude's tool context  
3. **Search-in-Prompt** — Search results embedded directly in the prompt (simulating Claude Code web search behavior)

For each method, the app calculates:
- **Token count**: How many tokens the search result consumes when sent to Claude
- **Cost**: Token count × Claude model's per-token rate (scaled to 1,000 searches)

The UI renders a comparison table with the **lowest-cost option highlighted** (yellow left border + "Most Efficient" badge).

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+ (for UI)
- uv (Python package manager): `pip install uv`
- pnpm (Node package manager): `npm install -g pnpm`
- Docker (for production container build)

### Local Development

1. **Clone and setup environment:**
   ```bash
   cd Benchmark-Tavily
   cp .env.template .env
   # Edit .env with your TAVILY_API_KEY
   ```

2. **Install dependencies:**
   ```bash
   just sync
   ```

3. **Run the app:**

   **Option A: Docker (recommended for production-like environment)**
   ```bash
   just docker-build
   just docker-run # docker run -p 8080:8080 --env-file .env benchmark-tavily:latest
   # Visit http://localhost:8080
   ```

   **Option B: Local development (separate processes)**
   ```bash
   # Terminal 1: Start FastAPI backend (run from repo root - api/ uses absolute imports)
   uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

   # Terminal 2: Start SvelteKit dev server
   cd ui && pnpm dev

   # Visit http://localhost:5173 (UI dev server proxies /api to localhost:8000)
   ```

## Project Structure

```
api/                    # Python FastAPI backend
├── main.py             # App entry point, lifespan
├── routers/
│   └── benchmark.py    # GET /api/benchmark endpoint
├── services/           # Business logic
│   ├── fixture_manager.py
│   ├── token_calculator.py
│   └── search_executor.py
├── models/
│   └── schemas.py      # Pydantic request/response models
├── tests/              # Unit tests (pytest)
└── fixtures/           # Cached API responses (committed to git)

ui/                     # SvelteKit + Tailwind frontend
├── src/
│   ├── routes/         # SvelteKit pages
│   ├── lib/
│   │   ├── api-client.ts
│   │   ├── models.ts
│   │   └── components/
│   └── app.css
├── tests/              # Playwright E2E tests
└── package.json

scripts/
├── fixtures/
│   └── record_fixtures.py  # Record real API responses (one-time)
└── hooks/              # Pre-commit hooks

.github/workflows/      # CI/CD
├── fast_commit.yml     # Lint/typecheck/test on push
└── full_pr.yml         # Docker build + Playwright on PR
```

## Architecture

### Runtime Topology

```
Browser (static SvelteKit build)
  ↓ /api/benchmark
  ↓
nginx (reverse proxy, Port 8080)
  ├→ /api/* → FastAPI (localhost:8000)
  └→ / → static files
```

### Data Flow

1. **Startup (one-time):** `python scripts/fixtures/record_fixtures.py` fetches real responses and caches them
2. **Request time:** GET `/api/benchmark` reads fixtures, tokenizes with tiktoken, calculates cost, returns JSON
3. **UI:** Renders comparison table with winner-highlight pattern

## Development

### Running Tests

```bash
# Python unit tests
just api-test

# TypeScript type checking
just ui-typecheck

# Playwright E2E tests
just ui-test

# Run all validation (lint, format, typecheck, tests)
just check
```

### Code Style

All code follows [AgentSoul standards](https://github.com/synechron/skills):

- **Python:** Black formatter, Ruff linter, MyPy type checker
- **TypeScript:** Biome v2 (lint/format), strict tsconfig
- **Pre-commit hooks:** Automated via prek.toml (secrets, formatting, linting)

Install pre-commit hooks:
```bash
prek install
```

### Fixture Management

Fixtures (cached API responses) are committed to git for reproducible testing.

**To update fixtures** (after API changes):
```bash
python scripts/fixtures/record_fixtures.py
# Commit api/fixtures/ changes
```

## Deployment

### Vercel

The app is designed for deployment to Vercel as a **Container**:

1. Link the GitHub repo to Vercel
2. Vercel auto-detects `Dockerfile.vercel` and deploys as a Container
3. Every push to `main` triggers a production deployment
4. Every PR gets a preview deployment

**Environment variables** in Vercel:
- `TAVILY_API_KEY` (Repository secret)

### Docker Build Locally

```bash
docker build -t benchmark-tavily .
docker run -p 8080:8080 --env-file .env benchmark-tavily:latest
```

## Design

High-fidelity design mockup: [design_handoff_benchmark_tavily/Benchmark-Tavily.dc.html](design_handoff_benchmark_tavily/Benchmark-Tavily.dc.html)

Key UI patterns:
- **Winner highlight:** Yellow left border (4px) + "Most Efficient" badge + shadow
- **Tab switcher:** Summary (default) / Searches (stub)
- **Model selector:** Dropdown to switch between Haiku, Sonnet, Opus

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## Tech Stack

**Backend:**
- FastAPI (async HTTP framework)
- Uvicorn (ASGI server)
- Tavily Python SDK
- tiktoken (token counting)
- Pydantic (data validation)
- OpenTelemetry (observability)

**Frontend:**
- Svelte 5 (reactive components)
- SvelteKit (framework, static adapter)
- Tailwind CSS + shadcn-svelte (styling & components)
- Playwright (E2E testing)

**Infrastructure:**
- Docker (containerization)
- nginx (reverse proxy)
- GitHub Actions (CI/CD)
- Vercel (deployment)

## License

MIT
