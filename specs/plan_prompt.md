Build a benchmarking app to measure the impact of the cost Tavily web search tool. These web search will be compared:
- Claude Code web search tool
- Tavily CLI
- Tavily MCP
These web search tools will be compared with a fixed set of "web search queries".

Searches will be run once at startup from a saved file to be created called `searches.yaml` that includes the fields `query`, `note`, `successfuly_return_includes`. the queries included to start with are:

- return the latest release of the package `uv`
- what is the current stable version of the Svelte compiler
- what does the Tavily extract API endpoint return

Each cell = `tiktoken` token count + $ price (at a stated reference model's per-token rate) of that response payload if fed to an LLM - not Tavily's own request pricing. Claude Sonnet 5 token cost is the most important comparative benchmark, with an added UI selector to change the Anthropic model: Haiku, Opus, etc.

Record real responses once via a script (with a TAVILY_API_KEY in `.env` file) as checked-in fixtures under api/fixtures/; default runtime, CI, and tests all replay fixtures - no live calls in CI.

## Architecture

Build:
- Python API:
    - `uv` controled,
    - FastAPI backend (api/): GET /api/benchmark that compares Agent raw web search with Tavily, both CLI and Tavily MCP; against raw claude code web search
    - `uvicorn` as the API web server

- TypeScript UI: using Svelte
    - `SvelteKit` + `shadcn-svelte` frontend (apps/ui) renders the table (Raw tool call, MCP) with "web search query" data-testid selectors.
    - nginx web server
- `otel` collecting claude code usage telemetry
- a multistage dockerfile building it all together in one container
    - including vercel deployment
- Playwright test asserts the table renders.
A run file built with `justfile`

Build .gitignore & README.md for everything.

## Testing

- unittest will be use dto write unit tests, multiple for every method
- Playwright will be written to validate the UI loads, and check that `Tavily` is included in the output.

## GitHub Actions

Two GitHub Actions

- fast_commit: lint/typecheck/unit-test etc., on commit
- full_pr: docker build, Playwright test, on PR

### Pre-commit hooks

- include: type checking, secrets detection with gitleaks, linting, formatting and standard git pre-commit hooks

### Secrets
The `TAVILY_API_KEY` has been stored in a GitHub Actions Repository secret.
A .env must be created to house this locally.

## Design

The design has been completed in Claude Design: `@.\design_handoff_benchmark_tavily\`

## Documentation search

- Always use Context7 when I need library/API documentation, code generation, setup or configuration steps without me having to explicitly ask.


## AgentSoul Memory

Location: `@C:\Users\newt0b\Code\Agent_Context\`

- A store of widely applicable decisions, conventions, and major architectural choices
- AgentSoul is it's own repo: update it's files directly.
- Follow `llm-wiki` pattern for pages and links, with OKF mardkwon format frontmatter that includses `type:`
- Before writing a /plan, search AgentSoul for prior knowledge, conventions, architecture patterns
- Update AgentSoul after every major decision and major implementation

Start here: `@C:\Users\newt0b\Code\Agent_Context\AgentSoul Index.md`

### Imports

In addition to identifying relevant info following pages must be imported and actioned, likely in sub agents and implemented in seperate worktrees.

The following must be found in the `AgentSoul Index`:

- Approved Dependencies
- Python coding standards
- fastapi patterns
- TypeScript Coding Standards
- Svelte Application Patterns
- Logging conventions

- env file usage
- Ignore file policy
- Pre-commit hooks
- Testing Strategy
- Repository Workflow

Import and implement in sub agents:

- GitHub Actions Standards
- Dependency pinning
- Justfile usage
- Vercel Deployment

When implementing loop: write tests first, check pre-commit hooks pass, docker build + playwright test until green.

Write the plan to `@.\specs\Benchmark-Tavily-build-plan.md`.
Ask any useful questions.
