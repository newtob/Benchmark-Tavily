# Contributing to Benchmark-Tavily

Thank you for contributing to this benchmarking project! This document outlines our development practices and requirements.

### Python

- **Formatter:** Ruff
- **Linter:** Ruff
- **Type Checker:** MyPy (strict mode)
- **Style:** PEP 8, Google-style docstrings

Run formatting & linting:
```bash
just api-fmt-fix   # Auto-fix formatting issues
just api-lint-check  # Check linting
just api-typecheck   # Run type checker
```

### TypeScript / JavaScript

- **Formatter & Linter:** Biome v2
- **Type Checker:** TypeScript (strict mode)
- **Package Manager:** pnpm with `strict-peer-dependencies`

Run formatting & linting:
```bash
just ui-lint-fix   # Auto-fix formatting issues
just ui-typecheck  # Type check
```

## Testing

### Python Unit Tests

```bash
just api-test          # Run all tests
just api-test-watch    # Run in watch mode
```

Tests should:
- Mock external dependencies (Tavily API, fixtures)
- Test public contracts (routes, services)
- Include type hints
- Use `pytest` fixtures in `conftest.py`

### UI Tests (Playwright)

```bash
just ui-test       # Run E2E tests
just ui-test-ui    # Run with interactive UI
```

Tests should:
- Use stable `data-testid` selectors
- Test visible user outcomes
- Avoid implementation details
- Work in headless mode (CI)

## Pre-Commit Hooks

All commits are validated with pre-commit hooks. Install them:

```bash
prek install
```

Hooks include:
- Secret scanning (gitleaks)
- Python formatting (ruff)
- Python type checking (mypy)
- TypeScript formatting (biome)
- Trailing whitespace, large files, etc.

If a hook fails, fix the issue or run auto-fixers:
```bash
just fmt-fix  # Auto-fix formatting
```

## Architecture

### Backend (FastAPI)

- **Route layer** (`routers/`): HTTP handling, validation, status codes
- **Service layer** (`services/`): Business logic, state changes, external calls
- **Models** (`models/schemas.py`): Pydantic request/response contracts

See [[fastapi_patterns]] for patterns and rules.

### Frontend (SvelteKit)

- **Components** (`src/lib/components/`): Reusable UI building blocks
- **Routes** (`src/routes/`): Page-level components
- **API client** (`src/lib/api-client.ts`): Typed HTTP requests

See [[Svelte Application Patterns]] for patterns.

## Pull Requests

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes** and ensure all tests pass:
   ```bash
   just check   # Full validation: lint, format, typecheck, tests
   ```

3. **Commit with descriptive messages** (conventional commits):
   ```
   feat: add model selector dropdown
   fix: correct token calculation for Sonnet 5
   docs: update README with deployment steps
   ```

4. **Push and create a PR:**
   - Title: Clear, descriptive
   - Description: What changed and why
   - Link any related issues

5. **CI pipeline:**
   - `fast_commit.yml`: Runs on every push (lint, typecheck, tests)
   - `full_pr.yml`: Runs on PRs (Docker build, Playwright tests)
   - All checks must pass before merging

## Design Reference

High-fidelity design mockup: [design_handoff_benchmark_tavily/](design_handoff_benchmark_tavily/)

The UI implements a **winner-highlight pattern**:
- Lowest-cost comparison option gets a yellow left border, badge, and shadow
- See design mockup for exact spacing, colors, and typography

## Fixtures

Fixture data (cached API responses) is committed to git for reproducible testing.

**To update fixtures** after changes to search logic:
```bash
# Requires .env with TAVILY_API_KEY
python scripts/fixtures/record_fixtures.py

# Commit the changes
git add api/fixtures/
git commit -m "chore: update test fixtures"
```

## Local Development

### Quick Start

```bash
cp .env.template .env
# Edit .env with TAVILY_API_KEY

just sync          # Install all dependencies
just docker-build  # Build Docker image
docker run -p 8080:8080 --env-file .env benchmark-tavily:latest
# Visit http://localhost:8080
```

### Alternative: Run Services Separately

```bash
# Terminal 1: Python API (run from repo root - api/ uses absolute imports)
uv run uvicorn api.main:app --reload

# Terminal 2: SvelteKit dev
cd ui && pnpm dev

# Visit http://localhost:5173 (UI auto-proxies /api to backend)
```

## Debugging

### Python API

```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
uv run uvicorn api.main:app --reload --log-level debug

# Run tests with output
pytest api/tests/ -v -s

# Type checking in strict mode
mypy api/ --show-error-codes --show-error-context
```

### SvelteKit UI

```bash
# Dev server with hot reload
cd ui && pnpm dev

# Build & preview production
cd ui && pnpm build && pnpm preview

# Debug Playwright tests
cd ui && pnpm exec playwright test --debug
```

## Documentation

- **Code comments:** Explain *why*, not *what*. Code should read clearly.
- **Docstrings:** Google-style, on all public functions/classes
- **README:** Update with major feature changes
- **This file:** Update if development practices change

## Performance & Security

### Performance

- Use fixtures (cached data) in tests; no live API calls in CI
- Minimize token calculation overhead (cache where reasonable)
- Profile before optimizing

### Security

- Never commit secrets (`.env`, API keys, tokens)
- Use `python-dotenv` for local development
- Secrets in CI: GitHub Actions secrets only
- Validate all external input with Pydantic/Zod schemas

## Questions?

- Check existing issues and PRs
- Review AgentSoul standards linked throughout
- Ask in code comments or open a discussion

Thank you for keeping this project high-quality and maintainable!
