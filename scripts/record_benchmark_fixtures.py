#!/usr/bin/env python3
"""
One-off script: makes real calls against Tavily (raw + MCP + extract) and
the Claude Code CLI (headless web search), and writes the results into
api/fixtures/** as the fixtures the served app replays. See
specs/tavily-benchmark-app.md §4.

Usage:
    just record-fixtures
    # or directly:
    TAVILY_API_KEY=... python3 scripts/record_benchmark_fixtures.py

Requires:
- TAVILY_API_KEY in the environment (for the three Tavily calls).
- The Claude Code CLI installed and logged in (`claude /login`) on this
  machine (for the Claude Web Search leg) — there is no env-var credential
  for this leg; see api/services/claude_web_search.py.

Known unresolved risk: whether this org's Claude Code entitlement permits
headless (`-p`) invocation at all is unverified. If the Claude leg fails
with an auth/entitlement error, that's the actual answer to that open
question — see specs/tavily-benchmark-app.md §4's note on this.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.services import benchmark_inputs, claude_web_search, tavily_extract, tavily_mcp, tavily_raw

HERE = Path(__file__).resolve().parent.parent
FIXTURES = HERE / "api" / "fixtures"


def _write(directory: Path, index: int, recording: object) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{index}.json"
    with open(path, "w") as f:
        json.dump(dataclasses.asdict(recording), f, indent=2)  # type: ignore[call-overload]
    print(f"wrote {path}")


async def record_tool_call_fixtures(api_key: str) -> None:
    queries = benchmark_inputs.load_tool_call_queries()
    for i, q in enumerate(queries):
        print(f"[tool_call {i}] raw: {q.query!r}")
        raw = tavily_raw.invoke(q.query, api_key=api_key)
        _write(FIXTURES / "tool_call" / "raw", i, raw)

        print(f"[tool_call {i}] mcp: {q.query!r}")
        mcp = await tavily_mcp.invoke(q.query, api_key=api_key)
        _write(FIXTURES / "tool_call" / "mcp", i, mcp)


async def record_web_content_fixtures(api_key: str) -> None:
    pairs = benchmark_inputs.load_web_content_pairs()
    for i, p in enumerate(pairs):
        print(f"[web_content {i}] tavily_extract: {p.url!r}")
        extracted = tavily_extract.invoke(p.url, api_key=api_key)
        _write(FIXTURES / "web_content" / "tavily_extract", i, extracted)

        print(f"[web_content {i}] claude_web_search: {p.question!r}")
        recording = await claude_web_search.invoke_cli(p.question)
        _write(FIXTURES / "web_content" / "claude_web_search", i, recording)


async def main() -> None:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        print("error: TAVILY_API_KEY is not set", file=sys.stderr)
        sys.exit(1)

    await record_tool_call_fixtures(api_key)
    await record_web_content_fixtures(api_key)

    print(
        "\nDone. Before committing, eyeball the fixture files under api/fixtures/ "
        "for anything account-identifying beyond the query/URL/question text itself."
    )


if __name__ == "__main__":
    asyncio.run(main())
