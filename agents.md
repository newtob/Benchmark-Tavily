# Agents.md

This file provides guidance to coding agents (Claude Code, GitHub Copilot, etc.)
working in this repository. `CLAUDE.md` is a thin pointer to this file — this
is the source of truth.

## Repository state

TypeScript and Python components, hosted on Vercel, source-controlled on
GitHub. Current content: OpenTelemetry tooling under `otel/` for capturing
Claude Code's own per-prompt token usage and cost, plus the repo-wide tooling
scaffold (pre-commit, CI, dependency management) described below. No
deployable application exists yet — once one is added (e.g. a Next.js app
under `apps/`), Vercel's native GitHub integration handles preview/production
deploys; no custom GitHub Actions deploy step is needed for that.

## File structure

```text
Tavily-Benchmark/
├── justfile                    # primary command surface — `just --list` for everything
├── prek.toml                   # pre-commit (Prek) hook configuration
├── scripts/hooks/               # wrapper scripts backing local prek hooks
├── .github/workflows/
│   ├── ci.yml                  # quality (prek), test (pytest + vitest), dependency review
│   └── codeql.yml              # SAST for JS/TS + Python
├── .mcp.json                    # GitHub + Context7 MCP servers
├── .env.template                 # documented env var contract (no vars required yet)
├── renovate.json                 # dependency-update bot config
├── pyproject.toml                 # Python tooling: uv, ruff, mypy, pytest
├── tests/                         # pytest suite
├── package.json, pnpm-workspace.yaml, .npmrc  # TypeScript tooling (pnpm workspace)
├── tsconfig.json, tsconfig.build.json, biome.json, reset.d.ts
├── apps/*, packages/*            # reserved for future TS packages (pnpm workspace globs; empty for now)
└── otel/
    ├── docker-compose.yml         # otel-collector-contrib container
    ├── otel-collector-config.yaml # OTLP receiver → file exporter for logs+metrics
    ├── parse_prompt_costs.py      # groups api_request events by prompt.id
    └── output/                    # captured JSONL + parsed costs (gitignored)
```

## Commands

`just` is the primary entry point — run `just --list` for the full,
authoritative set of recipes (grouped: `otel`, `py`, `ts`, `all`). Highlights:

- `just install` — install both Python (`uv sync --group dev`) and TypeScript
  (`pnpm install`) toolchains.
- `just check` — run the full local quality gate (`prek run --all-files`):
  formatting, linting, type checking, and secret scanning for both languages.
- `just ci` — everything CI runs: `check` plus `py-test` (pytest) and
  `ts-test` (vitest).
- `just py-lint` / `py-format` / `py-typecheck` / `py-test` — individual
  Python steps (ruff, ruff, mypy, pytest).
- `just ts-lint` / `ts-format` / `ts-typecheck` / `ts-test` — individual
  TypeScript steps (Biome, Biome, tsc, Vitest). `ts-typecheck` skips cleanly
  when there are no `.ts`/`.tsx` files yet.
- `just otel-up` / `otel-parse` / `otel-costs` / `otel-down` — the OTel
  per-prompt cost capture flow (see below).

## Repository conventions

Applying Synechron SPEED standards and this vault's own conventions (see
AgentSoul below) to a polyglot TypeScript + Python repo:

- **TypeScript**: strict `tsconfig.json` (`noUncheckedIndexedAccess`,
  `exactOptionalPropertyTypes`, `verbatimModuleSyntax`, `erasableSyntaxOnly`,
  no `enum`, no `any`/`as`/`!`), Biome v2 for lint+format (never ESLint or
  Prettier alongside it), pnpm workspace (`apps/*`, `packages/*`) with
  `strict-peer-dependencies=true`, Vitest, Zod for boundary validation,
  `@total-typescript/ts-reset` wired via `reset.d.ts`.
- **Python**: `uv`-managed `pyproject.toml`, `ruff` for lint+format, `mypy
  --strict`, `pytest`. `otel/parse_prompt_costs.py` is the current Python
  component; its tests live in `tests/` (pytest `pythonpath = ["otel"]`).
- **Pre-commit**: Prek (`prek.toml`), installed via `prek install`. Baseline
  `pre-commit-hooks` (whitespace/EOF/YAML/JSON/large-files/merge-conflicts) +
  `betterleaks`/`gitleaks` secret scan + `ruff-check`/`ruff-format` + `mypy` +
  Biome + a `tsc` wrapper that skips when no TS files exist. Claude Code's
  `TaskCompleted` hook should call `prek run --config prek.toml --files
  $(git diff HEAD --name-only)` before finishing any task (registered in
  `.claude/settings.json` — **not yet wired up**; a permission classifier
  blocked that specific write, so add it by hand).
- **Git workflow**: short-lived `<type>/<description>` branches (Conventional
  Commit types), Conventional Commit messages, PR review with at least one
  approval and passing CI, squash merge into `main`.
- **CI (GitHub Actions)**: `ci.yml` runs `prek run --all-files` (quality),
  `pytest` + `vitest run` (tests), and `actions/dependency-review-action` on
  PRs; `codeql.yml` runs CodeQL SAST for JavaScript/TypeScript and Python on
  PRs, pushes to `main`, and a weekly schedule. All actions are pinned to
  exact tags (no floating `@main`/`@v1`).
- **Dependencies**: every direct dependency pinned to an explicit version
  (`renovate.json` handles updates — `config:recommended`, grouped
  non-major bumps auto-merged for devDependencies, `typescript`/
  `@biomejs/biome` pinned exactly).
- **MCP**: `.mcp.json` configures the GitHub MCP server (remote, hosted) and
  Context7, both reading credentials from environment variables
  (`GITHUB_MCP_TOKEN`, `CONTEXT7_API_KEY`) — never hardcoded.
- **Secrets/env**: no secrets committed. `.env.template` documents the
  contract (currently no application env vars — only the optional MCP
  tokens above); GitHub Actions secrets for CI; Vercel's dashboard/`vercel
  env` for anything a deployed app needs at runtime.

## Architecture: OTel per-prompt cost tracking (`otel/`)

Claude Code's built-in `/cost` only reports cumulative session totals, not a per-prompt breakdown. This repo's `otel/` setup reconstructs **per-prompt** cost by capturing Claude Code's own telemetry:

- `.claude/settings.local.json` sets `CLAUDE_CODE_ENABLE_TELEMETRY=1` and points the OTLP exporters at `localhost:4317` (gRPC). This is read only at process startup, so it takes effect on the *next* `claude` launch, not the currently running session.
- `otel/docker-compose.yml` + `otel/otel-collector-config.yaml` run an `otel/opentelemetry-collector-contrib` container that receives OTLP logs/metrics and writes them as newline-delimited JSON (`otel/output/otel-logs.jsonl`, `otel/output/otel-metrics.jsonl`). The `file` exporter requires the **contrib** collector image, not the core one.
- `otel/parse_prompt_costs.py` reads that JSONL, filters to `claude_code.api_request` log events, and groups them by the `prompt.id` attribute (shared by every event/API call belonging to one user turn) to sum `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`, and `cost_usd` per prompt.
- `otel/output/` is gitignored — it holds local captured telemetry state, not something to commit.

`cost_usd` is Claude Code's own internal cost estimate, not a reconciled billing figure.

## AgentSoul Memory Policy

Location: `@/Users/bennewton/Ai/AgentSoul/AgentSoul/`

- Store memories, conventions, and major architectural choices.
- AgentSoul is its own repository; update its files directly without committing as part of this repository's work
- Use OKF markdown format with frontmatter that includes `type:`
- Follow the `llm-wiki` pattern for pages and links
- Before every /plan, search AgentSoul for relevant prior knowledge, conventions, architectural decisions, and known gaps
- Update AgentSoul after every major architecture, contract, CI/CD, security, operational, or incident-driven change
- Dependency upgrades and documentation-only changes are not major unless they alter an established convention or contract
- The purpose of AgentSoul is to capture this repository's way of working so future projects can reuse proven knowledge and practices
