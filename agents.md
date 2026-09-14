# Agents.md

This file provides guidance to coding agents (Claude Code, GitHub Copilot, etc.)
working in this repository. `CLAUDE.md` is a thin pointer to this file — this
is the source of truth.

## Repository state

TypeScript and Python components, source-controlled on GitHub. Current
content: OpenTelemetry tooling under `otel/` for capturing Claude Code's own
per-prompt token usage and cost (plus a prompt journal correlating that cost
with the actual prompt text — see below); the repo-wide tooling scaffold
(pre-commit, CI, dependency management); and the Tavily Benchmark app
(`api/` + `apps/ui/`) — see `specs/tavily-benchmark-app.md` for its design
and `specs/otel-collector-autostart.md` for the OTel autostart/journal
design. The app ships as a single local Docker container (`Dockerfile`),
not deployed anywhere yet; a future Vercel deploy of `apps/ui` (SvelteKit,
natively supported) is a reasonable low-effort follow-up but out of scope
for now.

## File structure

```text
Tavily-Benchmark/
├── specs/                       # design docs: the app, OTel autostart/journal
├── justfile                    # primary command surface — `just --list` for everything
├── prek.toml                   # pre-commit (Prek) hook configuration
├── scripts/hooks/               # wrapper scripts backing local prek hooks + Claude Code hooks
├── scripts/record_benchmark_fixtures.py  # regenerates api/fixtures/**
├── .github/workflows/
│   ├── ci-commit.yml           # fast: prek + pytest + vitest, on every push
│   ├── ci-pr.yml                # full: ci-commit + dependency-review + docker build + Playwright
│   └── codeql.yml               # SAST for JS/TS + Python
├── .mcp.json                    # GitHub + Context7 MCP servers
├── .env.template                 # documented env var contract
├── renovate.json                 # dependency-update bot config
├── pyproject.toml                 # Python tooling: uv, ruff, mypy, pytest
├── tests/                         # pytest suite
├── package.json, pnpm-workspace.yaml, .npmrc  # TypeScript tooling (pnpm workspace)
├── tsconfig.json, tsconfig.build.json, biome.json, reset.d.ts
├── api/                           # FastAPI backend for the Tavily Benchmark app
├── apps/ui/                       # SvelteKit + shadcn-svelte frontend
├── e2e/                            # Playwright, run against the built container
├── Dockerfile, docker/             # single-container build (nginx + uvicorn)
├── packages/*                      # reserved for future TS packages (empty for now)
└── otel/
    ├── docker-compose.yml         # otel-collector-contrib container (auto-started, see below)
    ├── otel-collector-config.yaml # OTLP receiver → file exporter for logs+metrics + health_check
    ├── parse_prompt_costs.py      # groups api_request events by prompt.id
    ├── join_prompt_journal.py     # joins prompt_costs.json against the prompt journal
    └── output/                    # captured JSONL + parsed costs (gitignored)
```

## Commands

`just` is the primary entry point — run `just --list` for the full,
authoritative set of recipes (grouped: `otel`, `py`, `ts`, `app`, `all`).
Highlights:

- `just install` — install both Python (`uv sync --group dev`) and TypeScript
  (`pnpm install`) toolchains.
- `just check` — run the full local quality gate (`prek run --all-files`):
  formatting, linting, type checking, and secret scanning for both languages.
- `just ci` — everything CI runs: `check` plus `py-test` (pytest) and
  `ts-test` (vitest).
- `just py-lint` / `py-format` / `py-typecheck` / `py-test` — individual
  Python steps (ruff, ruff, mypy, pytest).
- `just ts-lint` / `ts-format` / `ts-typecheck` / `ts-test` — individual
  TypeScript steps (Biome, Biome, svelte-check + tsc, Vitest).
- `just docker-build` / `docker-run` / `docker-check` / `e2e-install` /
  `e2e` / `e2e-full` — the Tavily Benchmark app's build/run/test loop; see
  `specs/tavily-benchmark-app.md`.
- `just record-fixtures` — regenerate the app's checked-in benchmark
  fixtures (needs `TAVILY_API_KEY` + a `claude /login`'d CLI).
- `just otel-up` / `otel-parse` / `otel-costs` / `otel-report` / `otel-down`
  — the OTel per-prompt cost capture + prompt-journal flow (see below).
  The collector auto-starts via a `SessionStart` hook; `otel-up`/`-down`
  are for manual troubleshooting only.

## Repository conventions

Applying Synechron SPEED standards and this vault's own conventions (see
AgentSoul below) to a polyglot TypeScript + Python repo:

- **TypeScript**: strict `tsconfig.json` (`noUncheckedIndexedAccess`,
  `exactOptionalPropertyTypes`, `verbatimModuleSyntax`, `erasableSyntaxOnly`,
  no `enum`, no `any`/`as`/`!`), Biome v2 for lint+format (never ESLint or
  Prettier alongside it — but Biome cannot reliably analyze `.svelte` files
  in-place, since it only sees each SFC's `<script>` block in isolation and
  produces false-positive unused-variable/import errors on props only
  referenced from the template; `.svelte` is excluded from `biome.json`'s
  `includes` and `svelte-check` is the authoritative linter/typechecker for
  it instead), pnpm workspace (`apps/*`, `packages/*`, `e2e`) with
  `strict-peer-dependencies=true`, Vitest, Zod for boundary validation,
  `@total-typescript/ts-reset` wired via `reset.d.ts`. **Known compatibility
  hold**: the root workspace pins `typescript@7.0.2`, but `apps/ui` pins
  `typescript@6.0.3` instead — `svelte-check`/`@sveltejs/kit` don't yet
  support TS 7 without a separate dual-version (`--tsgo`) setup this repo
  hasn't adopted. Root `tsconfig.json` excludes `apps/`/`packages/` from its
  own `include` so the two TypeScript projects stay isolated.
- **Python**: `uv`-managed `pyproject.toml`, `ruff` for lint+format, `mypy
  --strict`, `pytest`. `otel/parse_prompt_costs.py` and the `api/` FastAPI
  backend are the current Python components; tests live in `tests/` (pytest
  `pythonpath = ["otel", "."]`, so `api.*` imports resolve from repo root).
- **Pre-commit**: Prek (`prek.toml`), installed via `prek install`. Baseline
  `pre-commit-hooks` (whitespace/EOF/YAML/JSON/large-files/merge-conflicts) +
  `betterleaks`/`gitleaks` secret scan + `ruff-check`/`ruff-format` + `mypy`
  (covering `otel|tests|api|scripts`) + Biome + a `svelte-check`/`tsc`
  wrapper (`scripts/hooks/ts-typecheck.sh`) that checks the root TS project
  and `apps/ui` separately. Claude Code's `TaskCompleted` hook calls `prek
  run $(git diff HEAD --name-only)` before finishing any task; a
  `SessionStart` hook starts the OTel collector; a `UserPromptSubmit` hook
  logs the prompt journal (all in `.claude/settings.json`).
- **Git workflow**: short-lived `<type>/<description>` branches (Conventional
  Commit types), Conventional Commit messages, PR review with at least one
  approval and passing CI, squash merge into `main`.
- **CI (GitHub Actions)**: `ci-commit.yml` runs `prek run --all-files` +
  `pytest` + `vitest run` on every push (fast feedback, no Docker); `ci-pr.yml`
  runs all of that plus `actions/dependency-review-action`, a Docker build,
  and Playwright against the running container, on pull requests;
  `codeql.yml` runs CodeQL SAST for JavaScript/TypeScript and Python on
  PRs, pushes to `main`, and a weekly schedule. All actions are pinned to
  exact tags (no floating `@main`/`@v1`).
- **Dependencies**: every direct dependency pinned to an explicit version
  (`renovate.json` handles updates — `config:recommended`, grouped
  non-major bumps auto-merged for devDependencies, `typescript`/
  `@biomejs/biome` pinned exactly). The Tavily Benchmark app deliberately
  has **no** `anthropic` SDK dependency — see
  `specs/tavily-benchmark-app.md` §4/§7 for why.
- **MCP**: `.mcp.json` configures the GitHub MCP server (remote, hosted) and
  Context7, both reading credentials from environment variables
  (`GITHUB_MCP_TOKEN`, `CONTEXT7_API_KEY`) — never hardcoded.
- **Secrets/env**: no secrets committed. `.env.template` documents the
  contract — MCP tokens, plus `TAVILY_API_KEY`/`TAVILY_LIVE` for the
  benchmark app (needed only for `just record-fixtures`; the served app
  needs no secrets at all). There is deliberately no `ANTHROPIC_API_KEY` —
  this org doesn't issue one; see `specs/tavily-benchmark-app.md` §4.
  GitHub Actions secrets for CI (none currently required); this app is not
  deployed anywhere yet (local Docker only), so no deploy-time secrets
  exist either.

## Architecture: OTel per-prompt cost tracking (`otel/`)

Claude Code's built-in `/cost` only reports cumulative session totals, not a per-prompt breakdown. This repo's `otel/` setup reconstructs **per-prompt** cost by capturing Claude Code's own telemetry:

- `.claude/settings.json` sets `CLAUDE_CODE_ENABLE_TELEMETRY=1` and points the OTLP exporters at `localhost:4317` (gRPC), committed and on by default for anyone in this repo.
- A `SessionStart` hook (`scripts/hooks/otel-ensure-running.sh`) runs `docker compose -f otel/docker-compose.yml up -d` at the start of every session, so the collector is self-starting — `just otel-up` is now only needed for manual troubleshooting (e.g. after `just otel-down`).
- `otel/docker-compose.yml` + `otel/otel-collector-config.yaml` run an `otel/opentelemetry-collector-contrib` container that receives OTLP logs/metrics and writes them as newline-delimited JSON (`otel/output/otel-logs.jsonl`, `otel/output/otel-metrics.jsonl`). The `file` exporter requires the **contrib** collector image, not the core one.
- `otel/parse_prompt_costs.py` reads that JSONL, filters to `claude_code.api_request` log events, and groups them by the `prompt.id` attribute (shared by every event/API call belonging to one user turn) to sum `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`, and `cost_usd` per prompt.
- A `UserPromptSubmit` hook (`scripts/hooks/log-prompt.sh`, async) logs each prompt's text/timestamp to `otel/output/prompt_journal.jsonl`, keyed by the same `prompt_id` OTel uses. `just otel-report` (`otel/join_prompt_journal.py`) joins the two so you can see what a prompt actually was next to what it cost — see `specs/otel-collector-autostart.md` §5.
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
