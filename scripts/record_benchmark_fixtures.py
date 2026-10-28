#!/usr/bin/env python3
"""
One-off script: loads every benchmark page with Tavily Extract, TinyFish
Fetch (CLI) and the Claude Code CLI (headless WebFetch), and writes the
results into api/fixtures/web_content/** as the fixtures the served app
replays. See specs/tavily-benchmark-app.md §4/§17.

Usage:
    just record-fixtures
    # or directly (each leg can be selected):
    python3 scripts/record_benchmark_fixtures.py [--tavily-only|--tinyfish-only|--claude-only]

Requires (per leg):
- TAVILY_API_KEY in the environment (Tavily Extract).
- TINYFISH_API_KEY and the `tinyfish` CLI on PATH (TinyFish Fetch).
- The Claude Code CLI installed and logged in (`claude /login`) — there is no
  env-var credential for this leg; see api/services/claude_web_search.py.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.services import benchmark_inputs, claude_web_search, tavily_extract, tinyfish_fetch

HERE = Path(__file__).resolve().parent.parent
FIXTURES = HERE / "api" / "fixtures"
CLAUDE_PROMPT = (
    "Fetch {url} with the WebFetch tool and return the full text content of the page, "
    "verbatim, with no summary."
)


def _write(directory: Path, index: int, recording: object) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{index}.json"
    with open(path, "w") as f:
        json.dump(dataclasses.asdict(recording), f, indent=2)  # type: ignore[call-overload]
    print(f"wrote {path}")


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"error: {name} is not set", file=sys.stderr)
        sys.exit(1)
    return value


async def main() -> None:
    only = {a for a in sys.argv[1:] if a in ("--tavily-only", "--tinyfish-only", "--claude-only")}

    def want(flag: str) -> bool:
        return not only or flag in only

    tavily_key = _require("TAVILY_API_KEY") if want("--tavily-only") else None
    tinyfish_key = _require("TINYFISH_API_KEY") if want("--tinyfish-only") else None

    out = FIXTURES / "web_content"
    for i, page in enumerate(benchmark_inputs.load_web_content_pages()):
        if tavily_key:
            print(f"[page {i}] tavily_extract: {page.url!r}")
            _write(out / "tavily_extract", i, tavily_extract.invoke(page.url, api_key=tavily_key))
        if tinyfish_key:
            print(f"[page {i}] tinyfish_fetch: {page.url!r}")
            _write(
                out / "tinyfish_fetch",
                i,
                await tinyfish_fetch.invoke(page.url, api_key=tinyfish_key),
            )
        if want("--claude-only"):
            print(f"[page {i}] claude_web_search: {page.url!r}")
            recording = await claude_web_search.invoke_cli(CLAUDE_PROMPT.format(url=page.url))
            _write(out / "claude_web_search", i, recording)

    print(
        "\nDone. Before committing, eyeball the fixture files under api/fixtures/ "
        "for anything account-identifying."
    )


if __name__ == "__main__":
    asyncio.run(main())
