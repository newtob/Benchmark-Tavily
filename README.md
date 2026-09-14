# Tavily-Benchmark

TypeScript and Python components, deployed on Vercel, source-controlled on
GitHub. Currently holds OpenTelemetry tooling for capturing Claude Code's
per-prompt token usage and cost (`/cost` only reports cumulative session
totals) plus the repo's tooling scaffold — pre-commit hooks, CI, and
dependency management for both languages. See `agents.md` for full
conventions.

## Pricing

Tavily pricing:

- Charges by "credit", e.g 5 web page extractions per credit.
- Free tier is 1000 credits/month, which allows for 5000 web page extractions.
- Tavily then charges PaYG (Pay As You Go) at $0.008/credit, so the next 5000 web extractions would be $8 / £6.

Claude pricing:

- Each model's charges per input and output token, with a 90% discount on cache hit's within the default 5 min window.

## Getting started

```bash
just install   # uv sync + pnpm install
just check     # run the full local quality gate (prek: format, lint, typecheck, secrets)
just ci        # check + both test suites (pytest, vitest)
```

Run `just --list` for every available recipe, grouped by domain (`otel`,
`py`, `ts`, `all`).

## OTel per-prompt cost — typical flow

```bash
just otel-up      # start the OTel collector (docker compose, detached)
```

Exit this Claude Code session and run `claude` again in this repo — the
telemetry env vars in `.claude/settings.local.json` are only read at process
startup, so a running session won't pick them up.

Use Claude Code as normal for a while, then:

```bash
just otel-parse    # aggregate captured events into per-prompt token/cost totals
just otel-costs    # print the parsed summary
just otel-down     # stop the collector when you're done capturing
```

## Folder structure

```text
.
├── agents.md               # repository conventions and guidance (source of truth)
├── CLAUDE.md               # pointer to agents.md
├── justfile                # command runner — otel / py / ts / all recipe groups
├── prek.toml               # pre-commit (Prek) hook config
├── scripts/hooks/          # wrapper scripts backing local prek hooks
├── .github/workflows/      # ci.yml (quality + tests), codeql.yml (SAST)
├── .mcp.json               # GitHub + Context7 MCP servers
├── renovate.json           # dependency-update bot config
├── pyproject.toml, tests/  # Python tooling (uv, ruff, mypy, pytest)
├── package.json, pnpm-workspace.yaml, tsconfig*.json, biome.json  # TypeScript tooling
└── otel/
    ├── docker-compose.yml         # runs the otel-collector-contrib container
    ├── otel-collector-config.yaml # OTLP receiver -> file exporter (logs + metrics)
    ├── parse_prompt_costs.py      # groups api_request events by prompt.id
    └── output/                    # captured JSONL + parsed costs (gitignored)
```
