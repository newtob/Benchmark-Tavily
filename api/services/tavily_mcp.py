"""Table 1, "MCP" column: calls Tavily's hosted remote MCP server's
`tavily_search` tool — see specs/tavily-benchmark-app.md §4/§14.

Only `invoke()` is called live, and only by scripts/record_benchmark_fixtures.py
(when TAVILY_LIVE=1). The served app always replays recorded fixtures via
fixtures.py; parse_response() is shared so live-recorded and replayed data
are shaped identically.

Uses the official `mcp` Python SDK (v2.x — its client API changed
significantly from v1.x; verify `mcp.Client`'s exact signature against the
installed version if this breaks). Auth follows Tavily's documented remote-
endpoint pattern (API key as a URL query parameter), matching the header-
less style already used by this repo's other remote MCP servers
(`.mcp.json`'s GitHub/Context7 entries use a bearer header instead — Tavily's
own docs specifically document the query-param form for its hosted server).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from mcp import Client

MCP_URL_TEMPLATE = "https://mcp.tavily.com/mcp/?tavilyApiKey={api_key}"
SEARCH_TOOL_NAME = "tavily_search"


@dataclass(frozen=True)
class McpRecording:
    query: str
    response_text: str  # the tool result content, as text — tokenized by tokenizer.py
    latency_ms: float
    response_bytes: int


async def invoke(query: str, *, api_key: str) -> McpRecording:
    """Call Tavily's MCP `tavily_search` tool. Live-mode only."""
    started = time.monotonic()
    url = MCP_URL_TEMPLATE.format(api_key=api_key)
    async with Client(url) as client:
        result = await client.call_tool(SEARCH_TOOL_NAME, {"query": query})
    latency_ms = (time.monotonic() - started) * 1000
    return parse_response(query, result, latency_ms=latency_ms)


def parse_response(query: str, raw_result: Any, *, latency_ms: float) -> McpRecording:
    # MCP tool results carry a list of content blocks; join their text so the
    # tokenizer sees the same shape a model would when reading a tool result.
    content = getattr(raw_result, "content", raw_result)
    if isinstance(content, list):
        text_parts = [getattr(block, "text", str(block)) for block in content]
        response_text = "\n".join(text_parts)
    elif isinstance(content, dict):
        response_text = json.dumps(content)
    else:
        response_text = str(content)
    return McpRecording(
        query=query,
        response_text=response_text,
        latency_ms=latency_ms,
        response_bytes=len(response_text.encode()),
    )
