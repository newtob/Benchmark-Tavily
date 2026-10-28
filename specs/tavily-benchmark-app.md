# Tavily Benchmark App — Plan

Status: **implemented (v1)** — built and verified end-to-end (`just check`,
`just docker-build`/`docker-run`, `just e2e-full`), with placeholder
(not-yet-real) fixtures pending `just record-fixtures` — see §14.
Owner: Ben Newton
Scope: v1 (see "Out of scope" for deferred work)

## 1. Goal

Ship a small full-stack app that runs **two independent cost comparisons**
and displays each as its own HTML table:

1. **Tavily integration methods** — for the same Tavily search query, how
   does a raw tool call compare to going through Tavily's MCP server?
   Columns: **Raw tool call**, **MCP**.
2. **Web-content strategies** — for the same information need, how does
   letting Claude answer with its own web search tool compare to fetching
   a specific page with Tavily's web page extraction (extract) tool?
   Columns: **Claude Web Search**, **Tavily Extract**.

Both tables use the same cell shape: estimated **LLM tokens** and **$
price** for that method's response payload, plus latency/bytes as
secondary detail. A Python API produces both tables' data; a Svelte UI
(shadcn-svelte components) renders them. Everything packages into one
Docker container runnable locally, with a Playwright test that asserts
both tables render.

## 2. Decisions locked in during planning

These were resolved via clarifying questions before writing this plan —
recorded here so the "why" isn't lost:

| Question | Decision |
|---|---|
| What do "tokens"/"price" measure? | The **LLM token cost of the response payload** — how many tokens it would cost to feed each method's result to a model, and $ at a reference model's rate. Not Tavily's own request pricing. |
| What are Table 1's columns? | Exactly **2**: Raw tool call, MCP (Tavily's `search`, called two ways). |
| Does the Claude-web-search-vs-extract comparison replace Table 1? | **No** — it's a second, separate table. The app ships both comparisons. |
| What's a row in Table 2? | A **URL + question pair**: Tavily Extract is given the URL directly; Claude Web Search is given the question and must find/read a page itself. They solve the same underlying information need via two different strategies — not necessarily the identical page, which is realistic and avoids depending on search results being reproducible over time. |
| How is Table 2's cost computed? | **tiktoken estimate for both columns** — same methodology as Table 1, reusing `tokenizer.py`/`pricing.py` unchanged, so the two columns stay apples-to-apples. |
| Tokenizer | **`tiktoken`**, offline/deterministic. Documented as an approximation of Claude's real tokenizer, not exact. |
| Benchmark data source for CI/Playwright | **Recorded fixtures**: real Tavily calls + Claude Code CLI recordings run once locally, saved as checked-in fixtures. CI, the Docker build check, and Playwright all replay fixtures — no API keys or live network calls needed in GitHub Actions. |
| Frontend shape | **SvelteKit + `@sveltejs/adapter-static`**, compiled to static files served by nginx. shadcn-svelte's CLI targets SvelteKit. |
| Spec format | Plain markdown under `specs/` (this file) — not the OpenSpec CLI workflow. |
| How is Claude Web Search data obtained? | **No `ANTHROPIC_API_KEY` exists — org policy disables issuing one.** Recorded via the already-authenticated Claude Code CLI in headless mode (`claude -p`), fixture-only, never at request time. See §4/§6/§7/§14. |
| New dependencies | Approved as listed in §7. `anthropic` was considered and **removed** once `ANTHROPIC_API_KEY` turned out to be unavailable; `pyyaml` was added for the hand-curated benchmark-input files (below). |
| Benchmark input file format | **YAML** (`api/fixtures/*/inputs.yaml`), not JSON or Markdown — these are hand-curated, human-edited scenario definitions (comments explaining *why* a query was picked matter here), unlike the machine-recorded *response* fixtures, which stay JSON. See §4. |
| Capability scope | Table 1: Tavily `search` only. Table 2: Tavily `extract` + Claude's web search tool. `crawl`/`map` stay out of scope (see §15). |

## 3. Architecture

Follows this workspace's existing documented pattern for a small full-stack
app (single-container modular monolith, FastAPI + Svelte + nginx) rather
than inventing a new shape:

```text
browser → nginx (:8080) ──/api/*──→ uvicorn (127.0.0.1:8000, FastAPI)
                          └──/*────→ static SvelteKit build (adapter-static)
```

One container, one Dockerfile, one process-supervising entrypoint script
(no new supervisor dependency — nginx runs in the foreground as PID 1's
final `exec`, uvicorn is started first in the background by the entrypoint
script, matching the "minimal runtime image" convention).

```text
Tavily-Benchmark/
├── specs/
│   ├── tavily-benchmark-app.md          # this file
│   └── otel-collector-autostart.md
├── api/                                  # Python API (new)
│   ├── main.py                           # composition root: lifespan, routers
│   ├── routers/
│   │   └── benchmark.py                  # GET /api/benchmark, GET /api/healthz
│   ├── services/
│   │   ├── tavily_raw.py                 # Table 1: raw HTTP/tool-call path (tavily-python)
│   │   ├── tavily_mcp.py                 # Table 1: MCP client path (mcp SDK)
│   │   ├── claude_web_search.py          # Table 2: parses recorded Claude Code CLI fixtures — no live path, ever (see §4)
│   │   ├── tavily_extract.py             # Table 2: Tavily's extract endpoint (tavily-python)
│   │   ├── tokenizer.py                  # tiktoken-based token estimate, shared by both tables
│   │   ├── pricing.py                    # reference model + $/1M-token constant, shared
│   │   ├── benchmark_inputs.py           # loads the hand-curated inputs.yaml files (below)
│   │   └── fixtures.py                   # loads recorded response fixtures when not live
│   ├── models/
│   │   └── schemas.py                    # BenchmarkCell + both tables' row/response models
│   └── fixtures/
│       ├── tool_call/
│       │   ├── inputs.yaml               # Table 1's hand-curated query set (YAML, see §4)
│       │   ├── raw/*.json                # recorded raw-tool-call responses
│       │   └── mcp/*.json                # recorded MCP responses
│       └── web_content/
│           ├── inputs.yaml               # Table 2's hand-curated URL+question set (YAML, see §4)
│           ├── claude_web_search/*.json  # recorded Claude Code CLI (`claude -p`) fixtures
│           └── tavily_extract/*.json     # recorded Tavily extract responses
├── scripts/
│   └── record_benchmark_fixtures.py      # one-off: real Tavily calls + `claude -p` → api/fixtures/
├── apps/
│   └── ui/                               # SvelteKit app (new; pnpm workspace already globs apps/*)
│       ├── src/routes/+page.svelte       # single page: fetch + render both tables
│       ├── src/lib/api.ts                # typed API client (fetch /api/benchmark)
│       ├── src/lib/components/ui/        # shadcn-svelte components (table, etc.)
│       └── svelte.config.js              # adapter-static
├── e2e/
│   ├── playwright.config.ts
│   └── tables.spec.ts                    # asserts both benchmark tables render
├── docker/
│   ├── nginx.conf
│   └── entrypoint.sh
├── Dockerfile                            # multi-stage: node build → python runtime
├── .dockerignore
├── tests/                                # existing pytest suite, extended
│   └── test_benchmark_service.py
├── prek.toml                             # extended (see §9)
├── .gitignore                            # extended (see §9)
├── README.md                             # extended (see §9)
└── .github/workflows/
    ├── ci-commit.yml                     # new: fast, on every push
    └── ci-pr.yml                         # new: full, on pull_request
```

## 4. Backend design (`api/`)

Follows this workspace's FastAPI conventions: routers own HTTP concerns,
services own business logic and external calls, `main.py` is the
composition root, `response_model` declared on every route.

- **`GET /api/healthz`** — liveness only, no downstream dependency check
  (per Runtime Architecture convention: a dependency outage must not fail
  liveness). Returns `{"status": "ok"}`.
- **`GET /api/benchmark`** — returns one `BenchmarkResponse` covering both
  tables:

  ```python
  class BenchmarkCell(BaseModel):
      tokens: int
      price_usd: float
      latency_ms: float
      response_bytes: int


  class ToolCallRow(BaseModel):
      query: str
      tavily_rest: BenchmarkCell
      tavily_mcp: BenchmarkCell
      tinyfish_cli: BenchmarkCell
      tinyfish_mcp: BenchmarkCell


  class WebContentRow(BaseModel):
      url: str
      question: str
      claude_web_search: BenchmarkCell
      tavily_extract: BenchmarkCell


  class BenchmarkResponse(BaseModel):
      model: str  # reference model the token/price estimate is based on
      tool_call_rows: list[ToolCallRow]
      web_content_rows: list[WebContentRow]
      generated_at: datetime
  ```

### Benchmark input files (hand-curated, YAML)

The "searches to run" — Table 1's fixed queries and Table 2's URL+question
pairs — live in two hand-curated **YAML** files, loaded by
`api/services/benchmark_inputs.py`:

```yaml
# api/fixtures/tool_call/inputs.yaml
# Hand-curated benchmark scenarios for Table 1 (Tavily REST/MCP vs TinyFish CLI/MCP).
# Edit this file to add/remove/adjust what the benchmark measures;
# recorded response fixtures are generated from it via `just record-fixtures`.
tool_call_queries:
  - query: "return the latest release for the package `uv`"
    note: >
      Exercises a real-world "check current package version" lookup —
      the kind of query a coding agent runs constantly.
```

```yaml
# api/fixtures/web_content/inputs.yaml
web_content_pairs:
  - url: "https://example.com/some-page"
    question: "What does this page say about X?"
    note: "Why this pair was chosen."
```

**YAML over JSON/Markdown**: these are editorial, human-maintained
scenario definitions — someone will add/tweak entries over time and wants
to explain *why* a query was chosen, so comments and readable multi-line
strings matter. That's different from the machine-recorded *response*
fixtures (`raw/*.json`, `mcp/*.json`, `claude_web_search/*.json`,
`tavily_extract/*.json`), which stay JSON — opaque, machine-generated
blobs nobody hand-edits. Markdown was considered and rejected: parsing
hand-written prose back into structured query/URL/question fields
reliably needs more custom-parsing code than either alternative, for no
benefit over YAML on a file nobody views outside an editor.

### Data source selection

A single `TAVILY_LIVE` env var (default unset/false) gates Table 1's and
Table 2's *Tavily* services only:

- Unset/false (default, and always true in CI/Docker-build-check/Playwright):
  `services/fixtures.py` loads every recorded `api/fixtures/**/*.json`
  response fixture, keyed by query (Table 1) or URL+question (Table 2).
- Live (local, manual): `tavily_raw.py`/`tavily_mcp.py` call Tavily's real
  `search`; `tavily_extract.py` calls Tavily's real `extract` endpoint.
  Requires `TAVILY_API_KEY`.

**`claude_web_search.py` has no live/request-time path at all, ever** —
regardless of `TAVILY_LIVE`, it only parses whatever's recorded in
`api/fixtures/web_content/claude_web_search/`. There is no
`ANTHROPIC_API_KEY` and no way to call Anthropic's API directly from this
org, so the served app (and the fixture-replay path used by CI/Docker/
Playwright) never attempts a live Claude call. Its shape:

```python
@dataclass(frozen=True)
class ClaudeWebSearchRecording:
    question: str
    response_text: str  # the CLI's `result` field — tokenized identically
    # to tavily_extract's content by tokenizer.py
    latency_ms: float  # wall-clock subprocess time — NOT apples-to-apples
    # with tavily_extract's raw-HTTP latency (see §6)
    response_bytes: int  # len(response_text.encode()) — payload-text bytes
    session_id: str  # provenance/debugging only; never read by pricing.py
    model: str  # the --model value actually used


def invoke_cli(
    question: str, *, model: str, timeout_s: float = 120
) -> ClaudeWebSearchRecording: ...
def parse_cli_result(question: str, raw_json: dict) -> ClaudeWebSearchRecording: ...
```

`invoke_cli()` is called **only** by `scripts/record_benchmark_fixtures.py`
— never by the running API service. Both recording and fixture-replay
funnel through `parse_cli_result()`, so live-recorded and replayed data are
shaped identically.

Either way, the same `services/tokenizer.py` + `services/pricing.py` turn
a response payload into `{tokens, price_usd}` for **every** column in both
tables — recorded fixtures are raw provider JSON/text, not pre-baked token
counts, so the estimate logic is exercised identically in live and fixture
mode.

### `scripts/record_benchmark_fixtures.py`

A one-off script (`just record-fixtures`), run locally, that:

- calls `tavily_raw`/`tavily_mcp` for each query in
  `api/fixtures/tool_call/inputs.yaml` (needs `TAVILY_API_KEY`);
- calls `tavily_extract` for each pair in
  `api/fixtures/web_content/inputs.yaml` (needs `TAVILY_API_KEY`);
- calls the Claude Code CLI in headless mode for each pair's `question`:

  ```bash
  claude -p "<question>" --output-format json --allowedTools "WebSearch" \
    --disallowedTools "Bash,Read,Write,Edit,WebFetch,Task" \
    --permission-mode default --permission-prompts none --model <alias>
  ```

  matching `pricing.py`'s `REFERENCE_MODEL` (needs the Claude Code CLI
  installed and logged in — `claude /login` — on this machine; **not** an
  env var, unlike everything else in this repo, so say so explicitly
  wherever this is documented). The JSON's `result` field becomes
  `response_text`; `total_cost_usd`/`usage`/`session_id` are captured for
  provenance/debugging only, never wired into `price_usd`. **The
  subprocess explicitly unsets `CLAUDE_CODE_ENABLE_TELEMETRY` and all
  `OTEL_*` env vars** so these recording calls never land in the same OTel
  stream as normal dev-session telemetry — keeps this cleanly separate
  from `specs/otel-collector-autostart.md`'s prompt-journal pipeline, per
  that spec's own §0 boundary.

  Flags to verify against the installed CLI version rather than trust
  blindly: `--permission-prompts none` (needs a recent-enough version;
  `--permission-mode dontAsk` is the documented fallback), whether
  `--allowedTools` alone already excludes everything else or the explicit
  `--disallowedTools` list is required, and the exact `--model` value
  syntax.

- writes every raw response into the matching `api/fixtures/` subtree.

Before committing, eyeball the output for anything account-identifying
beyond the query/URL/question text itself (the existing
gitleaks/betterleaks pre-commit hook also runs over these files).

**Known unresolved risk**: whether this org's Claude Code entitlement
permits headless (`-p`) invocation at all is unverified — the first real
`just record-fixtures` run is the actual test. If it's blocked too, Table
2's Claude column needs a different data source (e.g. hand-authored
synthetic fixtures) — a follow-up decision, not solved here. Until
verified, hand-authored placeholder fixtures (realistic but not CLI-
generated) unblock the rest of the pipeline (tests, Docker, Playwright).

## 5. Frontend design (`apps/ui/`)

- SvelteKit, `@sveltejs/adapter-static`, TypeScript, Svelte 5 runes for the
  page's local state (per this workspace's Svelte convention: any value
  assigned from an async callback like the `onMount`/fetch result must be
  `$state(...)`, not plain `let`).
- One route (`src/routes/+page.svelte`): on mount, fetch `/api/benchmark`
  through a small typed client (`src/lib/api.ts`), then render **two**
  shadcn-svelte `Table` components:
  - **Table 1** — Query | Tavily REST | Tavily MCP | TinyFish CLI | TinyFish MCP.
  - **Table 2** — URL / Question | Claude Web Search | Tavily Extract | TinyFish Fetch.

  Each method-column cell shows tokens and price (latency as secondary /
  tooltip value). Loading, empty, and error states per the UI Behavior
  Contract convention, independent per table (one table's fetch failing
  shouldn't blank out the other, if they end up as separate requests).
- Stable `data-testid`s, distinct per table so Playwright can address each
  independently:
  - Table 1: `data-testid="tool-call-table"`, headers
    `col-tavily-rest` / `col-tavily-mcp` / `col-tinyfish-cli` / `col-tinyfish-mcp`.
  - Table 2: `data-testid="web-content-table"`, headers
    `col-claude-search` / `col-tavily-extract` / `col-tinyfish-fetch`.
  - Plus a per-row testid on both tables.
- Built as static output (`apps/ui/build/` via adapter-static) and copied
  into the final Docker stage for nginx to serve.
- `chadcn` used for the design and component library. Use the preset `--preset b1OocktRFA`

## 6. Token/price methodology

- Tokenizer: `tiktoken`, using the `o200k_base` encoding (GPT-4o/o-series/
  GPT-5 family's encoding — the closest available offline stand-in for a
  modern large-vocabulary tokenizer; `cl100k_base` is the older/smaller
  alternative). Documented as an approximation, not exact Claude
  tokenization, in `api/services/tokenizer.py`'s docstring and in the UI.
  Used identically for all four columns across both tables.
- Pricing: a single reference model + published $/1M-input-token rate,
  defined as named constants in `api/services/pricing.py`
  (`REFERENCE_MODEL = "claude-sonnet-5"`, `PRICE_PER_MILLION_TOKENS_USD =
  2.0` — Claude Sonnet 5's standard input-token rate per
  platform.claude.com/docs/en/about-claude/pricing as of September 2026,
  cited in a code comment next to the constant; re-verify before relying
  on it beyond relative comparison between methods).
- `price_usd = tokens / 1_000_000 * PRICE_PER_MILLION_TOKENS_USD`.
- Table 2 note: the Claude Code CLI's recorded response also carries real
  Anthropic-billed cost data (`total_cost_usd`, `usage`) — this plan
  deliberately captures that for provenance/debugging only and does
  **not** surface it as `price_usd`, to keep both of Table 2's columns
  computed the same estimated way. Recording the real figure alongside
  the estimate is a reasonable v2 addition (see §15).
- Latency caveat: Table 2's `latency_ms` is **not** apples-to-apples
  between its two columns — Claude Web Search's figure is a CLI
  subprocess/agentic round-trip (heavier), Tavily Extract's is a raw HTTP
  call. Tokens/price stay comparable; latency is secondary/informational.

## 7. New dependencies (approved)

None of these existed in the repo's manifests before this plan
(`pyproject.toml` had zero runtime deps; `package.json` had only `zod`).
Pin every one to its current latest stable version at implementation time,
verified against its registry per this repo's dependency-pinning
convention — do not guess a version from training data.

**Python** (`pyproject.toml` → `[project].dependencies`):
`fastapi`, `uvicorn` (with the `standard` extra), `tavily-python`, `httpx`
(direct REST calls for the raw/extract paths), `mcp` (official Anthropic
MCP Python SDK, for Table 1's MCP column), `tiktoken`, `pyyaml` (for the
benchmark-input YAML files in §4). **`anthropic` is explicitly NOT a
dependency** — considered when Table 2 was first scoped, then removed once
`ANTHROPIC_API_KEY` turned out to be unobtainable (see §4); Claude Web
Search data comes from the Claude Code CLI instead, via stdlib
`subprocess`/`asyncio.create_subprocess_exec`, invoked only by the
recording script.

**TypeScript** (`apps/ui/package.json`, new workspace member):
`svelte`, `@sveltejs/kit`, `@sveltejs/adapter-static`, `@sveltejs/vite-plugin-svelte`,
`vite`, `tailwindcss` + `@tailwindcss/vite`, `clsx` + `tailwind-merge` (the
`cn()` helper), `svelte-check`. The `Table` component set was hand-authored
to match shadcn-svelte's structure (`Root`/`Header`/`Body`/`Row`/`Head`/
`Cell`) rather than run through its interactive CLI, since this
implementation ran non-interactively; a `components.json` is still present
so a future `shadcn-svelte add <component>` works normally. **Compatibility
hold**: `apps/ui` pins `typescript@6.0.3`, not the root workspace's
`typescript@7.0.2` — `svelte-check`/`@sveltejs/kit`'s peer ranges don't yet
accept TS 7 without a separate dual-version (`--tsgo`) setup; revisit once
they do. Biome cannot reliably lint/format `.svelte` files (it only sees
each SFC's `<script>` block in isolation, so it false-positives on props
only used in the template) — `.svelte` is excluded from `biome.json`'s
`includes`, and `svelte-check` is the sole linter/typechecker for those
files (this resolves the open item below about Biome's `.svelte` coverage:
it does attempt to cover them, incorrectly, so it's been turned off for
them instead).

**`e2e/` workspace member**: `@playwright/test`, `@types/node`.

**Dev-only**: `respx` (Python HTTP-mocking, for future service-level unit
tests beyond what `tests/test_benchmark_service.py` currently covers) and
`types-PyYAML`.

## 8. Docker

- Multi-stage `Dockerfile` at repo root:
  1. `node` stage — installs `apps/ui` deps, runs the SvelteKit
     static build.
  2. `python` stage — installs API dependencies via `uv` (no dev group) into
     the runtime image.
  3. Final minimal runtime stage — pinned slim base image, non-root user,
     copies only: the built static assets, the installed Python
     environment, `api/` source, `api/fixtures/`, `docker/nginx.conf`,
     `docker/entrypoint.sh`. No compilers, no `node_modules`, no test
     tooling, no Claude Code CLI (it's only ever invoked by the recording
     script on a developer's machine, never in the container).
- `docker/entrypoint.sh`: starts `uvicorn` bound to `127.0.0.1:8000` in the
  background, waits for it to answer `/api/healthz`, then `exec`s `nginx
  -g "daemon off;"` as the foreground process.
- `docker/nginx.conf`: listens on `8080`; proxies `/api/` to
  `127.0.0.1:8000`; serves the static build for everything else.
- `HEALTHCHECK` directive hits `http://localhost:8080/api/healthz`.
- `.dockerignore` excludes `node_modules/`, `.venv/`, test caches, `e2e/`,
  `.git/`, local env files.
- Runs with `TAVILY_LIVE` unset by default → fixture mode for both tables,
  so `docker run -p 8080:8080 <image>` works with no secrets at all.

## 9. Repo hygiene (public repo)

- **`.gitignore`** additions: `apps/ui/.svelte-kit/`, `apps/ui/build/`,
  `e2e/test-results/`, `e2e/playwright-report/`, `e2e/.cache/` (Playwright
  browser cache stays out of git; installed in CI via
  `playwright install --with-deps chromium`).
- **`prek.toml`** additions: extend the existing `mypy` hook's `files`
  pattern to include `api/.*\.py$`; extend the Biome hook's coverage
  implicitly (already matches `.ts`/`.svelte`... confirm Biome's file glob
  covers `.svelte` or add it explicitly); consider a Dockerfile-lint hook
  (`hadolint`) as a `local`/`docker` hook if it stays self-contained and
  fast — optional, not blocking.
- **`README.md`**: add a short section describing the app — both tables,
  what each one's raw-vs-MCP and Claude-web-search-vs-extract comparison
  shows, the tokens/price methodology one-liner and its approximation
  caveat — plus the three commands to run it (`just docker-build`, `just
  docker-run`, open `http://localhost:8080`), and how to regenerate
  fixtures (`just record-fixtures`, requires `TAVILY_API_KEY` and the
  Claude Code CLI installed + logged in — no `ANTHROPIC_API_KEY` exists).
- **`.env.template`**: document `TAVILY_API_KEY` (required only for `just
  record-fixtures`) and `TAVILY_LIVE` (optional, local-only toggle). Add a
  comment explaining there is no `ANTHROPIC_API_KEY` — the Claude Web
  Search fixture leg is recorded via the Claude Code CLI's own login,
  which is unusual for this repo (everything else is an env var) so it's
  worth calling out explicitly.

## 10. `justfile` additions

New recipes (grouped, per existing convention):
- `record-fixtures` — run `scripts/record_benchmark_fixtures.py`. Needs
  `TAVILY_API_KEY` and the Claude Code CLI installed + authenticated
  (`claude /login`) on this machine — no API key for the Claude leg.
- `docker-build` — `docker build -t tavily-benchmark:local .`
- `docker-run` — run the image, publish `8080`.
- `docker-check` — build, run, poll `/api/healthz`, then curl `/` — a fast
  local sanity loop before reaching for Playwright.
- `e2e-install` — `pnpm --dir e2e exec playwright install --with-deps chromium`.
- `e2e` — run the container (or assume it's already running at a
  `PLAYWRIGHT_BASE_URL`), then `pnpm --dir e2e exec playwright test`.
- `e2e-full` — `docker-build` + `docker-run` (detached) + `e2e` + tear the
  container down, exit non-zero on failure. This is the recipe CI's PR
  workflow calls, and the one the implementation loop (§13) iterates on.

## 11. Testing

- **Unit (pytest)**: `tests/test_benchmark_service.py` — exercise
  `tokenizer.py` and `pricing.py` directly (deterministic given fixed
  input text), and both tables' fixture-mode assembly end-to-end against
  `api/fixtures/`. Router-level test with `TestClient` asserting
  `/api/benchmark`'s `response_model` shape (both row lists populated) and
  `/api/healthz`.
- **Playwright (`e2e/tables.spec.ts`)**: point at the running container,
  navigate to `/`, then for **each** table: wait for its `data-testid`
  root, assert its two header-column testids are present, assert at least
  one data row, and assert each cell's text contains both a token count
  and a `$` price. Single chromium project, no real-API opt-in needed
  since the container defaults to fixture mode for both tables.

## 12. CI/CD — two workflows

- **`.github/workflows/ci-commit.yml`** (new; replaces the `quality` +
  `test` jobs of today's `ci.yml` for the push case) — triggers on `push`
  to any branch. Fast feedback: `prek run --all-files` (format/lint/
  typecheck/secrets), `pytest`, `vitest run --passWithNoTests`. No Docker,
  no Playwright.
- **`.github/workflows/ci-pr.yml`** (new) — triggers on `pull_request`.
  Runs everything `ci-commit.yml` runs, plus: `actions/dependency-review-action`
  (moved here from today's `ci.yml`), `docker build`, run the container
  detached, install Playwright browsers, run the e2e suite against it
  (`just e2e-full`), and archive the Playwright report/traces as a build
  artifact on failure.
- `codeql.yml` stays as-is (already covers PR + push-to-main + weekly
  schedule; no change needed).
- Today's single `ci.yml` gets superseded by these two — delete it as part
  of implementation rather than running three workflows in parallel.
- All new/changed action pins stay exact-tag, per existing convention.
- Neither workflow needs any live credential — fixture mode only, and the
  Claude leg has no live path to begin with.

## 13. Delivery approach for implementation

Implementation proceeded as a build-test loop: scaffold → `just
docker-build` → `just docker-run` → `just docker-check` → run Playwright
against it → on any failure, inspect container logs/Playwright trace, fix,
and repeat. This is exactly what happened in practice — several real
failures were hit and fixed this way (a `vite.config.ts` import bug, a
`prerender` config gap, a TypeScript-version peer conflict, a root
`tsconfig.json`/Biome cross-project contamination issue) before `just
e2e-full` passed clean.

## 14. Resolved during implementation, and what's still genuinely open

**Resolved** (verified against live registries/docs/builds, not guessed):
- Tavily's search/extract endpoints, auth header, and hosted MCP endpoint
  (`https://mcp.tavily.com/mcp/?tavilyApiKey=...`, `tavily_search` tool) —
  confirmed via current Tavily docs.
- `claude -p` flags: `--output-format json` returns `result`/`session_id`/
  `total_cost_usd`/`usage`; `--permission-prompts none` requires Claude
  Code v2.1.259+ (fallback `--permission-mode dontAsk`); `--allowedTools`
  alone (no `--disallowedTools`) is sufficient given `--permission-mode
  default` + `--permission-prompts none` already deny anything not
  explicitly allowed — confirmed via current CLI docs.
- Tokenizer encoding (`o200k_base`) and pricing constant (`claude-sonnet-5`,
  $2/1M input tokens) — see §6.
- All dependency versions — verified against PyPI/npm directly at
  implementation time (see §7).
- Biome's `.svelte` coverage — it does attempt to parse them, incorrectly;
  excluded instead (see §7).
- `apps/ui`'s TypeScript version — pinned to 6.0.3, a documented
  compatibility hold against the root workspace's 7.0.2 (see §7).
- Root `tsconfig.json` needed an `apps`/`packages` exclusion, and
  `scripts/hooks/ts-typecheck.sh` needed to typecheck `apps/ui` separately
  (via `svelte-check`) — otherwise the root project's `tsc` (with
  `erasableSyntaxOnly`) tried to check `apps/ui`'s files under its own,
  incompatible ruleset. Fixed in both places.
- The otel-collector-contrib image ships no shell (`sh`, `wget`, `curl` all
  absent) — confirmed by attempting an exec healthcheck against it, which
  is why readiness is checked from the host script instead (see
  `specs/otel-collector-autostart.md` §3).
- Final query/pair sets in `api/fixtures/*/inputs.yaml` (3 each) — real,
  not placeholders; can be extended later.
- Root Vitest's default glob also matched `e2e/*.spec.ts`, trying (and
  failing) to run Playwright specs as Vitest tests — fixed with a root
  `vitest.config.ts` excluding `e2e/**`.
- Extending `prek.toml`'s mypy hook to cover `api`/`scripts` (§9) needed
  more than the `files` pattern change: the mypy pre-commit hook runs in
  its own self-contained environment with no access to this project's
  `.venv`, so without `additional_dependencies` listing `fastapi`,
  `pydantic`, and the rest, it silently resolved every `pydantic.BaseModel`
  subclass as `Any` instead of raising a real type error — passing when it
  shouldn't have, then intermittently failing depending on the hook
  environment's cache state. `uv run mypy` directly (using the real
  project `.venv`) never showed this, which is exactly why it went
  unnoticed initially. Fixed by adding `additional_dependencies` to the
  hook, pinned to the same versions as `pyproject.toml`.
- The whole pipeline (`just check`, `just ci`, `just docker-build`, `just
  docker-run`, `just e2e-full`) has been run for real during
  implementation and passes.

**Still genuinely open** (not blocking, per your answers):
- Whether this org's Claude Code entitlement permits headless (`-p`)
  invocation at all — unverified; the first real `just record-fixtures`
  attempt is the actual test (see §4). Until then, the checked-in
  `api/fixtures/web_content/claude_web_search/*.json` are hand-authored
  placeholders (marked with a `_placeholder_note` field), not real
  recordings — same for the Tavily fixtures, since no `TAVILY_API_KEY` was
  available during implementation either.
- Whether `UserPromptSubmit`'s hook JSON actually exposes prompt text (a
  separate, `specs/otel-collector-autostart.md`-owned question) — doesn't
  block this spec.

## 15. Out of scope for v1

- Tavily's `crawl`/`map` capabilities.
- Live Tavily calls or Claude Code CLI invocations inside GitHub Actions.
- Running the Claude Code CLI inside the served container or at HTTP-
  request time — Claude's column is fixture-only, always, by design.
- Correlating Table 2 recordings with the `otel/` per-prompt pipeline via
  `prompt_id` — a distinct, already-tracked concern, see
  `specs/otel-collector-autostart.md`'s prompt-journal section, not
  attempted here.
- A third "tavily-python SDK" column distinct from "raw tool call" in
  Table 1.
- Surfacing Claude web search's *real* Anthropic-billed usage next to the
  tiktoken estimate in Table 2 (see §6 note) — estimate-only for both
  columns in v1.
- Auth, persistence, historical trend tracking across benchmark runs.
- An Overmind-based hot-reload local dev inner loop (`Procfile`) — the
  Docker container is the only execution path this plan commits to; a
  faster dev loop can be added later without changing this architecture.

## 16. Vercel deployment

Added after the app was already built and verified locally, prompted by
the user asking how to publish it — see the decision trail below, since
the recommended approach changed mid-conversation as better information
became available.

### Decision trail

1. Checked the actual account state via the Vercel API rather than
   assuming: `newtob's projects` (hobby plan) had **zero linked
   projects** — the Vercel↔GitHub App connection existed at the account
   level, but no Vercel Project had ever been created for this repo.
2. Initially recommended restructuring `api/main.py` to serve the built
   SvelteKit output itself (`app.frontend()`), since Vercel's monorepo
   model is normally one Project per deployable directory and Vercel
   doesn't run arbitrary Docker containers for standard hosting — or so
   this plan believed at the time.
3. **That belief was wrong**, caught by verifying against current Vercel
   docs before implementing rather than after: Vercel now supports
   deploying an existing Dockerfile as a **Container** (a Vercel Function
   running the container image, Active CPU pricing, zero other config).
   This lets the already-built-and-verified single-container design
   deploy essentially unchanged — no FastAPI/frontend restructuring, no
   splitting into two Vercel Projects. Surfaced this correction and
   re-asked before implementing either path.

### What Container deployment requires (verified, not assumed)

- A file named exactly **`Dockerfile.vercel`** at the repo root — Vercel
  detects this filename and deploys it as a Container with no
  `vercel.json` needed.
- The containerized app must listen on Vercel's **`$PORT`** env var
  (assigned dynamically at runtime), not a hardcoded port.

### What changed in this repo

- **`Dockerfile.vercel`** — a symlink to `Dockerfile` (`ln -s Dockerfile
  Dockerfile.vercel`), not a duplicate file, so the two never drift.
  Verified `docker build -f Dockerfile.vercel .` resolves the symlink
  correctly. (Unverified: whether Vercel's own build pipeline follows a
  symlinked `Dockerfile.vercel` the same way a local Docker build does —
  a plain git clone preserves symlinks and Docker's `-f` flag follows
  them locally, so this is expected to work, but if Vercel's real build
  ever fails to resolve it, the fallback is to make `Dockerfile.vercel` a
  literal duplicate instead.)
- **`Dockerfile`**: added `ENV PORT=8080` (default for local `docker run`;
  Vercel overrides it at runtime) and the `HEALTHCHECK` now curls
  `http://localhost:${PORT}/api/healthz` instead of a hardcoded port.
- **`docker/nginx.conf`**: `listen 8080;` → `listen __PORT__;` (a
  placeholder, not literal nginx syntax).
- **`docker/entrypoint.sh`**: substitutes `__PORT__` with `${PORT:-8080}`
  into `/tmp/nginx.conf` (not `/etc/nginx/nginx.conf` in place — that
  path isn't writable by the non-root `appuser` this container runs as,
  which is exactly the kind of thing this app's own multi-stage
  `useradd`/`chown` setup exists to enforce) before `exec`-ing `nginx -c
  /tmp/nginx.conf -g "daemon off;"`.
- Verified for real: built via `-f Dockerfile.vercel`, ran with the
  default port (`docker run -p 8080:8080 ...`, no `-e PORT`) and with an
  explicit dynamic port (`-e PORT=3000 -p 3000:3000`) simulating what
  Vercel assigns at runtime — both serve `/`, `/api/healthz`, and
  `/api/benchmark` correctly, and Docker's own `HEALTHCHECK` reports
  `healthy` in both cases. `just e2e-full` (the default-port path) still
  passes unchanged.

### Linking and deploying (what actually happened)

- `create_git_project` (Vercel's API) reported creating a project but it
  never actually persisted — `get_project`/`list_projects` both returned
  nothing for it afterward. Root cause unconfirmed (propagation delay vs.
  a real failure); **do not retry this call blindly** — it explicitly
  warns not to create a second project under the same name.
- The Vercel **dashboard's own Import flow worked** where the API call
  didn't — used that instead once it was available (the GitHub App's
  per-repo grant had come through by then).
- **Gotcha hit after import**: a freshly imported project shows "no
  Production deployment yet" (`To deploy to production, push to master,
  or run vercel --prod`) — importing a repo does not, by itself, trigger
  a build. The GitHub webhook Vercel registers on import only fires on
  the *next* push to the production branch; a push that happened before
  the project existed doesn't retroactively trigger anything. Fixed by
  making a real commit (this section) and pushing to `master` again,
  now that the webhook is live.
- Confirm the Framework Preset actually resolved to **Container** after
  import (it should auto-detect from `Dockerfile.vercel`'s presence); if
  the dashboard shows anything else, override it manually before the
  first deploy.

## 17. TinyFish and the page-load re-focus (supersedes the search tables)

The benchmark now answers "which is the most token-efficient way of loading a
web page into a model?" as a three-way comparison of **page loads**: Claude
Code's WebFetch, Tavily Extract and TinyFish Fetch. The earlier search tables
(Tavily REST/MCP, TinyFish CLI/MCP) were dropped: search engines return
different pages and result counts, so their payloads cannot be made identical
across tools, whereas loading the same URL can.

- **Pages** (`api/fixtures/web_content/inputs.yaml`): 10 pages chosen to be
  static enough to repeat — three long Wikipedia articles, a fixed BBC
  article, letsencrypt.org, two small personal sites (one client-rendered),
  the GPL-3.0 text, RFC 1149 and example.com.
- **Methods**: `tavily_extract` (REST, markdown, basic depth);
  `tinyfish_fetch` (`tinyfish fetch content get <url> --format markdown`, CLI);
  `claude_web_search` (field name kept for fixture compatibility) is Claude
  Code headless with only the WebFetch tool; its tokens are the measured
  model-side ingestion of the tool result.
- **Recording**: `just record-fixtures` (`--tavily-only`, `--tinyfish-only`,
  `--claude-only` select a leg). The served app only replays fixtures.
- **Caveats**: (1) Claude's WebFetch summarises the page with a small model,
  so its token count is a summary, not the page; (2) some hosts are blocked
  (bbc.co.uk) — that fixture records the refusal and is an expected failure in
  the validity test; (3) a tool that fails or returns near-empty content scores
  few tokens, so the "most efficient" flag is not quality-adjusted; (4) TinyFish
  fetch may serve cached content (the CLI exposes no `ttl`).
