"""Public wire contract for GET /api/benchmark. See specs/tavily-benchmark-app.md §4."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BenchmarkCell(BaseModel):
    """One method's result for one benchmark row.

    `tokens`/`price_usd` are the primary, apples-to-apples metrics (see
    specs/tavily-benchmark-app.md §6) — a tiktoken estimate of this cell's
    response payload, priced at a fixed reference-model rate, identical
    across all four columns in both tables. `latency_ms`/`response_bytes`
    are secondary/informational and are NOT apples-to-apples across every
    column pair (see the §6 latency caveat for Table 2).
    """

    tokens: int
    price_usd: float
    latency_ms: float
    response_bytes: int


class ToolCallRow(BaseModel):
    """Table 1: Tavily raw tool call vs MCP, for one query."""

    query: str
    raw_tool_call: BenchmarkCell
    mcp: BenchmarkCell


class WebContentRow(BaseModel):
    """Table 2: Claude Web Search vs Tavily Extract, for one URL+question pair."""

    url: str
    question: str
    claude_web_search: BenchmarkCell
    tavily_extract: BenchmarkCell


class BenchmarkResponse(BaseModel):
    model: str
    tool_call_rows: list[ToolCallRow]
    web_content_rows: list[WebContentRow]
    generated_at: datetime
