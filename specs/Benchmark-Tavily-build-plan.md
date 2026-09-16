# Benchmark-Tavily Build Plan

Source spec: [`plan_prompt.md`](./plan_prompt.md). This document records the
architecture actually implemented, including where it deliberately deviates
from the spec or the Claude Design mockup, and why.

## Goal

Benchmark the LLM token-cost impact of three ways of getting web-search
results in front of Claude, using a fixed set of real, pre-recorded queries:

1. **`tavily_cli`** - a direct/raw call to the Tavily search API (via the
   `tavily-python` SDK - Tavily ships no actual `tavily` CLI binary, so the
   SDK is the faithful stand-in for "a raw tool call").
2. **`tavily_mcp`** - the same query routed through Tavily's official MCP
   server (`tavily-mcp` on npm), invoked over stdio via the `mcp` client SDK.
3. **`search_in_prompt`** - "raw Claude Code web search". Recorded by
   shelling out to the `claude` CLI itself (`claude -p`), not the Anthropic
   Messages API - see "search_in_prompt: no API key needed" below.

Each response is tokenized with `tiktoken` (an approximation - Claude has no
public tokenizer) and priced at a selected Anthropic model's published
per-token rate. Claude Sonnet 5 is the default reference model; Haiku 4.5 and
Opus 5 are also selectable.

## Architecture

```
Browser
  |  http://localhost:8080
  v
nginx (reverse proxy)
  |-> /api/*  -> FastAPI (127.0.0.1:8000)
  `-> /       -> static SvelteKit build (adapter-static, SPA fallback)

Data flow:
1. scripts/fixtures/record_fixtures.py records real API responses once
   (requires only TAVILY_API_KEY - see below for search_in_prompt) into
   api/fixtures/*.json.
2. GET /api/benchmark reads fixtures, tokenizes with tiktoken, prices with
   api/services/token_calculator.py::RATES, returns two comparison groups
   (token counts, cost) with 3 items each.
3. The UI renders both groups as cards, highlighting the lowest-cost method
   per group (yellow border + "MOST EFFICIENT" badge).
4. CI and the default runtime only ever replay committed fixtures - no live
   API calls happen outside record_fixtures.py.
```

## Known deviation from the Claude Design mockup

`design_handoff_benchmark_tavily/reference/Tavily_Benchmark_sample.html` was
built around a different data shape: two comparison pairs ("Raw tool call vs
MCP" and "Claude Web Search vs Tavily Extract") covering four distinct
methods, with results scaled ×1000 for readability. The implementation here
keeps the simpler, single-axis three-method model above (with the existing,
now-passing test suite built around it) rather than a redesign to four
methods and two comparison pairs. The visual language (yellow winner border,
badge, tab switcher, card layout, brand colors) was carried over faithfully;
the underlying comparison structure was not. Revisiting this - implementing
`tavily_extract` as a fourth method and splitting the two groups into
transport-vs-transport and content-vs-content comparisons - is the natural
next iteration if the product direction confirms the mockup's structure.

## Testing strategy

- `api/tests/*.py`: pytest (not stdlib `unittest` - the spec named
  `unittest`, but the codebase was already pytest-based end-to-end including
  fixtures/mocking; switching frameworks purely for the label wasn't worth
  the churn). Every service module (`fixture_manager`, `search_executor`,
  `token_calculator`) has a dedicated test file with multiple cases per
  method, including edge cases and error paths.
- `ui/tests/app.spec.ts`: Playwright, run against the built Docker container.
  Asserts the table renders, the winner badge shows, tabs switch (with
  `role="tab"`/`aria-selected`), "Tavily" appears in the content, and the
  model selector changes the request.
- CI never calls live Tavily/Anthropic APIs - both the API and the UI tests
  run against committed fixtures (or the empty-fixtures fallback, which
  returns a structurally valid zero-value response rather than erroring).

## Fixture data: recorded

`api/fixtures/*.json` holds 9 real, committed fixtures (3 queries x 3
methods).

## `search_in_prompt`: no Anthropic API key needed

Enterprise-managed Anthropic accounts may have no way to issue a standalone
API key at all, which rules out calling the Messages API directly (`tools:
[{"type": "web_search_..."}]`) to record this method. Instead,
`record_fixtures.py::search_in_prompt_search` shells out to the `claude`
CLI itself:

```
claude -p "Use the WebSearch tool to search for: <query>. Then use WebFetch \
  to fetch the content of the top 2 or 3 most relevant result URLs." \
  --strict-mcp-config \
  --allowedTools "WebSearch WebFetch" \
  --disallowedTools Bash,ToolSearch,Edit,Write,Read,Glob,Grep \
  --output-format stream-json --verbose
```

`--strict-mcp-config` (with no `--mcp-config`) disables all MCP servers so
it can't wander off into e.g. Context7 instead of searching the web;
`--disallowedTools` blocks every other built-in tool. The script then walks
the NDJSON transcript, correlates `tool_use` blocks named `WebSearch` or
`WebFetch` to their `tool_result` via `tool_use_id`, and joins the raw
result content across all matched calls into the fixture's `raw_response`.
This uses whatever authentication the local `claude` CLI already has - no
API key is read by this app for this method.

**Why WebFetch is included, not just WebSearch:** WebSearch alone returns
*only* a list of `{title, url}` pairs - zero page content - which made
`search_in_prompt` look 4-6x cheaper than Tavily in an early version of
this fixture set. That wasn't a capture bug, but it also wasn't a fair
comparison: Tavily's `search()` returns full extracted page content per
result by default, so comparing it against a bare link list was apples to
oranges. Following WebSearch with WebFetch on the top results means
`search_in_prompt` now actually retrieves page content too, closing most
(not all) of that gap. The remainder is real and expected: WebFetch's
`tool_result` is itself a Claude-generated answer extracted from the page,
governed by the `prompt` argument passed to it - by design more compact
than Tavily's raw content dump, not a shortcut taken here.

We considered Claude Code's built-in OTel telemetry
(`CLAUDE_CODE_ENABLE_TELEMETRY`) as an alternative, since `docker-compose.yml`
already stands up a collector for it. It doesn't fit: its metrics
(`claude_code.token.usage`, `claude_code.cost.usage`) are session-level
aggregates with no per-tool breakdown, so there's no way to isolate "what
did this one web_search call cost" from them. Its logs *can* carry raw tool
content (`OTEL_LOG_TOOL_CONTENT=1`), but that just gets you the same raw
text the CLI transcript above already gives you, with a collector pipeline
in between - equivalent data, more infrastructure. The OTel scaffolding in
this repo (collector service, `opentelemetry-*` deps) remains unwired.

## Environment

- Python 3.11 (pinned via `.python-version` - `tiktoken` has no prebuilt
  wheel for newer CPython versions yet, and no Rust toolchain is assumed).
- Node 20 + pnpm (version pinned via `ui/package.json`'s `packageManager`
  field; `ui/pnpm-lock.yaml` is committed and required for
  `pnpm install --frozen-lockfile` in Docker/CI).
