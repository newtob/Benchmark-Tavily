#!/usr/bin/env python3
"""Record real API responses from search methods into fixtures.

This script records responses from three distinct search methods so the
benchmark can compare their real token/cost footprints:

1. tavily_cli: A direct/raw call to Tavily's search API via the
   tavily-python SDK (the "raw tool call" path - Tavily ships no actual
   `tavily` CLI binary, so the SDK is the faithful equivalent).
2. tavily_mcp: The same query routed through Tavily's official MCP server
   (`tavily-mcp` on npm), invoked over stdio via the `mcp` client SDK.
3. search_in_prompt: "Raw Claude Code web search" - shells out to the
   `claude` CLI (`claude -p ... --output-format stream-json`), restricted
   to only the WebSearch tool, and extracts the raw WebSearch tool_result
   content from the transcript. This deliberately does NOT call the
   Anthropic Messages API directly: on an Enterprise-managed account a
   standalone Anthropic API key may not be issuable at all, but the
   `claude` CLI itself is already authenticated (SSO/OAuth/whatever the
   Enterprise plan provides), so shelling out to it needs no separate key.

Each fixture is saved as JSON with the following format:
{
    "method": "tavily_cli",
    "query": "search query text",
    "raw_response": "raw API response",
    "timestamp": "2026-09-14T12:34:56Z",
    "execution_time_ms": 234
}

Usage:
    python scripts/fixtures/record_fixtures.py

tavily_mcp needs the `mcp` package, which is intentionally NOT in the API's
pinned runtime dependencies (this script is a one-off maintenance tool, not
something that ships, and `mcp` pulls in a pydantic version newer than the
API's own pin). Install it into a throwaway environment before running:
    uv venv .venv-fixtures --python 3.11
    uv pip install --python .venv-fixtures tavily-python pyyaml python-dotenv mcp
    .venv-fixtures/bin/python scripts/fixtures/record_fixtures.py

search_in_prompt additionally needs the `claude` CLI on PATH and logged in
(`claude auth status` to check) - no Python package or API key required.

The script is idempotent - existing fixtures will be overwritten.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

METHODS = ["tavily_cli", "tavily_mcp", "search_in_prompt"]


class FixtureRecorder:
    """Records fixtures for search methods."""

    def __init__(self, tavily_api_key: str | None = None) -> None:
        """Initialize the fixture recorder.

        Args:
            tavily_api_key: Tavily API key. If None, loads from environment.

        Raises:
            ValueError: If TAVILY_API_KEY is not available.
        """
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        if not self.tavily_api_key:
            raise ValueError(
                "TAVILY_API_KEY not found in environment. " "Set it in .env or pass it as argument."
            )

        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent.parent
        self.fixtures_dir = self.project_root / "api" / "fixtures"
        self.searches_file = self.project_root / "searches.yaml"

        logger.info(f"Project root: {self.project_root}")
        logger.info(f"Fixtures directory: {self.fixtures_dir}")

    def load_searches(self) -> list[dict[str, Any]]:
        """Load search queries from searches.yaml.

        Returns:
            List of search dictionaries with a 'query' field.

        Raises:
            FileNotFoundError: If searches.yaml not found.
            ValueError: If searches.yaml is missing the 'searches' key.
        """
        if not self.searches_file.exists():
            raise FileNotFoundError(f"searches.yaml not found at {self.searches_file}")

        with open(self.searches_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "searches" not in data:
            raise ValueError("searches.yaml missing 'searches' key")

        searches = data["searches"]
        logger.info(f"Loaded {len(searches)} searches from searches.yaml")
        return searches

    def ensure_fixtures_dir(self) -> None:
        """Ensure api/fixtures directory exists."""
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Fixtures directory ready: {self.fixtures_dir}")

    def tavily_cli_search(self, query: str) -> tuple[str, int]:
        """Execute a raw/direct search against the Tavily API.

        Args:
            query: Search query string.

        Returns:
            Tuple of (raw_response, execution_time_ms).
        """
        from tavily import TavilyClient

        logger.info(f"Executing tavily_cli (raw tool call) search: {query}")
        client = TavilyClient(self.tavily_api_key)
        start_time = time.time()
        response = client.search(query)
        execution_time_ms = int((time.time() - start_time) * 1000)

        raw_response = json.dumps(response, default=str)
        logger.debug(f"tavily_cli response length: {len(raw_response)} chars")
        return raw_response, execution_time_ms

    def tavily_mcp_search(self, query: str) -> tuple[str, int]:
        """Execute a search via Tavily's official MCP server.

        Spawns `npx -y tavily-mcp@latest` over stdio and calls its
        `tavily_search` tool, exercising the real Model Context Protocol
        transport rather than a direct API call.

        Args:
            query: Search query string.

        Returns:
            Tuple of (raw_response, execution_time_ms).
        """
        logger.info(f"Executing tavily_mcp search: {query}")
        return asyncio.run(asyncio.wait_for(self._tavily_mcp_search_async(query), timeout=60))

    async def _tavily_mcp_search_async(self, query: str) -> tuple[str, int]:
        """Async implementation backing tavily_mcp_search."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "tavily-mcp@latest"],
            env={**os.environ, "TAVILY_API_KEY": self.tavily_api_key or ""},
        )

        start_time = time.time()
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("tavily_search", arguments={"query": query})
        execution_time_ms = int((time.time() - start_time) * 1000)

        if result.is_error:
            error_text = "\n".join(getattr(b, "text", "") for b in result.content)
            raise RuntimeError(f"tavily_mcp tool call returned an error: {error_text}")

        raw_response = "\n".join(block.text for block in result.content if hasattr(block, "text"))
        return raw_response, execution_time_ms

    # Tools search_in_prompt is allowed to use, and the ones whose results
    # get captured into the fixture payload. WebSearch alone only returns a
    # bare list of {title, url} - no page content at all - which isn't a
    # fair comparison against Tavily's results (which include full extracted
    # page content per result). Following up with WebFetch on the top
    # result URLs makes this "raw Claude Code web search" actually retrieve
    # information from the pages, not just list links.
    _SEARCH_IN_PROMPT_TOOLS = ("WebSearch", "WebFetch")

    def search_in_prompt_search(self, query: str) -> tuple[str, int]:
        """Execute a search+fetch via Claude Code's own WebSearch/WebFetch tools.

        Shells out to `claude -p ... --output-format stream-json`, locked to
        only WebSearch and WebFetch (no MCP servers, no other built-in
        tools), instructed to search then fetch the top result pages, and
        pulls the raw tool_result content for both out of the transcript.
        Uses whatever authentication the local `claude` CLI already has - no
        Anthropic API key needed, which matters on Enterprise-managed
        accounts where a standalone key isn't issuable.

        Note WebFetch's tool_result is itself a Claude-generated answer
        extracted from the page (governed by the `prompt` argument Claude
        passes to it), not raw page HTML/text - that's a real, inherent
        property of the tool, not a simplification made here.

        Args:
            query: Search query string.

        Returns:
            Tuple of (raw_response, execution_time_ms).

        Raises:
            RuntimeError: If the `claude` CLI isn't on PATH, the invocation
                fails, or it produced no WebSearch/WebFetch tool result at
                all.
        """
        if shutil.which("claude") is None:
            raise RuntimeError(
                "`claude` CLI not found on PATH; search_in_prompt requires "
                "the Claude Code CLI to be installed and logged in."
            )

        logger.info(f"Executing search_in_prompt (Claude Code WebSearch+WebFetch) search: {query}")
        start_time = time.time()
        result = subprocess.run(
            [
                "claude",
                "-p",
                f"Use the WebSearch tool to search for: {query}. Then use WebFetch "
                "to fetch the content of the top 2 or 3 most relevant result URLs.",
                "--strict-mcp-config",
                "--allowedTools",
                " ".join(self._SEARCH_IN_PROMPT_TOOLS),
                "--disallowedTools",
                "Bash,ToolSearch,Edit,Write,Read,Glob,Grep",
                "--output-format",
                "stream-json",
                "--verbose",
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=True,
        )
        execution_time_ms = int((time.time() - start_time) * 1000)

        raw_response = self._extract_tool_results(result.stdout, self._SEARCH_IN_PROMPT_TOOLS)
        if not raw_response:
            raise RuntimeError(
                f"claude -p produced no WebSearch/WebFetch tool result for query: {query!r}"
            )
        return raw_response, execution_time_ms

    @staticmethod
    def _tool_result_text(content: Any) -> list[str]:
        """Normalize a tool_result block's `content` field into text chunks."""
        if isinstance(content, str):
            return [content]
        if isinstance(content, list):
            return [
                c.get("text", "")
                for c in content
                if isinstance(c, dict) and c.get("type") == "text"
            ]
        return []

    @classmethod
    def _extract_tool_results(cls, stream_json_stdout: str, tool_names: tuple[str, ...]) -> str:
        """Pull matching tool_result content out of a `claude -p` stream-json transcript.

        Correlates `tool_use` blocks whose name is in `tool_names` to their
        matching `tool_result` blocks via `tool_use_id`, since a query can
        trigger more than one call (e.g. one WebSearch plus several
        WebFetch calls on the top results).

        Args:
            stream_json_stdout: Raw NDJSON stdout from `claude -p
                --output-format stream-json`.
            tool_names: Tool names whose tool_result content to capture.

        Returns:
            All matched tool_result contents, in transcript order, joined
            by blank lines. Empty string if none were found.
        """
        matching_tool_use_ids: set[str] = set()
        results: list[str] = []

        for line in stream_json_stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            message = event.get("message")
            content_blocks = message.get("content") if isinstance(message, dict) else None
            for block in content_blocks or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use" and block.get("name") in tool_names:
                    tool_use_id = block.get("id")
                    if isinstance(tool_use_id, str):
                        matching_tool_use_ids.add(tool_use_id)
                elif (
                    block.get("type") == "tool_result"
                    and block.get("tool_use_id") in matching_tool_use_ids
                ):
                    results.extend(cls._tool_result_text(block.get("content")))

        return "\n\n".join(results)

    def save_fixture(
        self,
        method: str,
        query: str,
        index: int,
        raw_response: str,
        execution_time_ms: int,
    ) -> Path:
        """Save fixture to JSON file.

        Args:
            method: Search method name (tavily_cli, tavily_mcp, search_in_prompt).
            query: Original search query.
            index: Index of the query in searches.yaml (0-based).
            raw_response: Raw response text from the API.
            execution_time_ms: Execution time in milliseconds.

        Returns:
            Path to the saved fixture file.
        """
        fixture = {
            "method": method,
            "query": query,
            "raw_response": raw_response,
            "timestamp": datetime.now(UTC).isoformat(),
            "execution_time_ms": execution_time_ms,
        }

        filename = self.fixtures_dir / f"searches_{method}_{index}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(fixture, f, indent=2)

        logger.info(f"Saved fixture: {filename}")
        return filename

    def record_fixtures(self) -> dict[str, int]:
        """Record all fixtures for all methods and queries.

        Returns:
            Dictionary with counts: {
                "total_fixtures": int,
                "successful": int,
                "failed": int,
                "skipped": int,
            }
        """
        searches = self.load_searches()
        self.ensure_fixtures_dir()

        stats = {"total_fixtures": 0, "successful": 0, "failed": 0, "skipped": 0}

        for method in METHODS:
            for query_idx, search_item in enumerate(searches):
                query = search_item["query"]
                stats["total_fixtures"] += 1

                try:
                    if method == "tavily_cli":
                        raw_response, execution_time_ms = self.tavily_cli_search(query)
                    elif method == "tavily_mcp":
                        raw_response, execution_time_ms = self.tavily_mcp_search(query)
                    elif method == "search_in_prompt":
                        raw_response, execution_time_ms = self.search_in_prompt_search(query)
                    else:
                        raise ValueError(f"Unknown method: {method}")

                    self.save_fixture(method, query, query_idx, raw_response, execution_time_ms)
                    stats["successful"] += 1

                except RuntimeError as e:
                    logger.warning(f"Skipping {method} (query {query_idx}): {e}")
                    stats["skipped"] += 1
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Error recording fixture for {method} query {query_idx}: {e}")
                    stats["failed"] += 1

        return stats


def main() -> int:
    """Main entry point for fixture recording.

    Returns:
        Exit code: 0 on success, 1 on failure.
    """
    parser = argparse.ArgumentParser(
        description="Record search fixtures for benchmarking.",
        epilog=(
            "Records real API responses from all three search methods into "
            "api/fixtures/ as JSON files. Idempotent - existing fixtures "
            "are overwritten. Methods needing credentials that aren't "
            "configured are skipped, not treated as failures."
        ),
    )
    parser.add_argument(
        "--api-key",
        help="Tavily API key (defaults to TAVILY_API_KEY env var)",
    )
    args = parser.parse_args()

    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded .env from {env_path}")

    try:
        recorder = FixtureRecorder(tavily_api_key=args.api_key)
        logger.info("Starting fixture recording...")
        stats = recorder.record_fixtures()

        logger.info("=" * 60)
        logger.info("Fixture Recording Summary")
        logger.info("=" * 60)
        logger.info(f"Total fixtures: {stats['total_fixtures']}")
        logger.info(f"Successful: {stats['successful']}")
        logger.info(f"Skipped (missing credentials): {stats['skipped']}")
        logger.info(f"Failed: {stats['failed']}")

        if stats["successful"] > 0:
            print(f"\nRecorded {stats['successful']} fixtures across {len(METHODS)} methods")

        return 0 if stats["failed"] == 0 else 1

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
