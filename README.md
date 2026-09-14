# Tavily-Benchmark

TypeScript and Python components, source-controlled on GitHub. Holds:

- The **Tavily Benchmark app** — two cost-comparison tables rendered as a
  small full-stack app (see below).
- OpenTelemetry tooling for capturing Claude Code's own per-prompt token
  usage/cost, plus a prompt journal correlating that cost with the actual
  prompt text.
- The repo's tooling scaffold — pre-commit hooks, CI, and dependency
  management for both languages.

See `agents.md` for full conventions, and `specs/` for the design docs
behind the app and the OTel tooling.

## Pricing

The benchmark app's own tokens/price columns are an **estimate** (tiktoken
counts, priced at a fixed reference model's rate — see
[`specs/tavily-benchmark-app.md`](specs/tavily-benchmark-app.md) §6), not
either provider's real billing. For context, here's what Tavily and Claude
actually charge:

Tavily pricing:

- Charges by "credit", e.g. 5 web page extractions per credit.
- Free tier is 1000 credits/month, which allows for 5000 web page extractions.
- Tavily then charges PAYG (Pay As You Go) at $0.008/credit, so the next 5000 web extractions would be $8 / £6.

Claude pricing:

- Each model charges per input and output token, with a 90% discount on cache hits within the default 5 min window.

## The Tavily Benchmark app

Two independent tables, each comparing tokens/price for a different pair
of methods:

1. **Tavily: Raw tool call vs MCP** — the same search query, called
   directly against Tavily's REST API vs through its hosted MCP server.
2. **Web content: Claude Web Search vs Tavily Extract** — the same
   underlying question, answered via Claude's own web search tool vs by
   extracting a specific page with Tavily's Extract API.

Full design: [`specs/tavily-benchmark-app.md`](specs/tavily-benchmark-app.md).

```bash
just install                 # uv sync + pnpm install
just docker-build             # build the app image
just docker-run                # run it, publishing :8080
```

Then open <http://localhost:8080>. The container always runs in fixture
mode — no API keys or network calls needed to see the tables.

```bash
just docker-check              # build + run + poll /api/healthz and /
just e2e-install                # one-time: install Playwright's browser
just e2e-full                   # build + run + Playwright + tear down
```

### Regenerating fixtures

```bash
TAVILY_API_KEY=... just record-fixtures
```

Needs `TAVILY_API_KEY` (Tavily's raw/MCP/extract calls) and the Claude
Code CLI installed and logged in (`claude /login`, no API key — this org
doesn't issue `ANTHROPIC_API_KEY`) for the Claude Web Search leg. Edit
`api/fixtures/tool_call/inputs.yaml` / `api/fixtures/web_content/inputs.yaml`
first to change what gets benchmarked.

### Deploying to Vercel

`Dockerfile.vercel` (a symlink to `Dockerfile`) lets Vercel deploy this
same container as a Container-type Vercel Function — see
[`specs/tavily-benchmark-app.md`](specs/tavily-benchmark-app.md) §16 for
what that required (mainly: the app listening on `$PORT` instead of a
hardcoded port). Not yet linked to a live Vercel project.

## Getting started

```bash
just install   # uv sync + pnpm install
just check     # run the full local quality gate (prek: format, lint, typecheck, secrets)
just ci        # check + both test suites (pytest, vitest)
```

Run `just --list` for every available recipe, grouped by domain (`otel`,
`py`, `ts`, `app`, `all`).

## OTel per-prompt cost — typical flow

The collector now auto-starts via a `SessionStart` hook — just open a
`claude` session in this repo and it's running. `just otel-up`/`otel-down`
remain available for manual troubleshooting.

```bash
just otel-parse    # aggregate captured events into per-prompt token/cost totals
just otel-costs    # print the parsed summary
just otel-report   # join costs against the logged prompt text/summary (by prompt_id)
just otel-down     # stop the collector when you're done capturing
```

A `UserPromptSubmit` hook logs each prompt's text/timestamp to
`otel/output/prompt_journal.jsonl`, keyed by the same `prompt_id` OTel
uses — `just otel-report` joins the two. See
[`specs/otel-collector-autostart.md`](specs/otel-collector-autostart.md).

## Folder structure

```text
.
├── agents.md               # repository conventions and guidance (source of truth)
├── CLAUDE.md               # pointer to agents.md
├── specs/                  # design docs: the app, and the OTel autostart/journal
├── justfile                # command runner — otel / py / ts / app / all recipe groups
├── prek.toml               # pre-commit (Prek) hook config
├── scripts/hooks/          # wrapper scripts backing local prek hooks + Claude Code hooks
├── scripts/record_benchmark_fixtures.py  # regenerates api/fixtures/**
├── .github/workflows/      # ci-commit.yml (quality + tests), ci-pr.yml (PR, incl. Docker+Playwright), codeql.yml (SAST)
├── .mcp.json               # GitHub + Context7 MCP servers
├── renovate.json           # dependency-update bot config
├── pyproject.toml, tests/  # Python tooling (uv, ruff, mypy, pytest)
├── package.json, pnpm-workspace.yaml, tsconfig*.json, biome.json  # TypeScript tooling
├── api/                    # FastAPI backend for the benchmark app
├── apps/ui/                # SvelteKit + shadcn-svelte frontend
├── e2e/                    # Playwright tests against the built container
├── Dockerfile, Dockerfile.vercel, docker/  # single-container build (nginx + uvicorn); .vercel is a symlink for Vercel's Container deploy mode
└── otel/
    ├── docker-compose.yml         # runs the otel-collector-contrib container (auto-started)
    ├── otel-collector-config.yaml # OTLP receiver -> file exporter (logs + metrics) + health_check
    ├── parse_prompt_costs.py      # groups api_request events by prompt.id
    ├── join_prompt_journal.py     # joins prompt_costs.json against the prompt journal
    └── output/                    # captured JSONL + parsed costs (gitignored)
```
