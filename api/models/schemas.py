"""Public wire contract for GET /api/benchmark. See specs/tavily-benchmark-app.md §4."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BenchmarkCell(BaseModel):
    """One method's result for one benchmark row.

    `tokens`/`price_usd` are the primary, apples-to-apples metrics (see
    specs/tavily-benchmark-app.md §6) — a token count for this cell's
    response payload (see `tokens_source`), priced at a fixed
    reference-model rate. `latency_ms`/`response_bytes`
    are secondary/informational and are NOT apples-to-apples across every
    column pair (see the §6 latency caveat for Table 2).
    """

    tokens: int
    price_usd: float
    latency_ms: float
    response_bytes: int
    # How `tokens` was obtained: "tiktoken_estimate" (o200k_base over the
    # recorded payload) or "claude_usage_measured" (the model's own usage
    # deltas for ingesting the WebSearch tool result — Claude column only).
    tokens_source: str = "tiktoken_estimate"


class WebContentRow(BaseModel):
    """One page load: Claude vs Tavily Extract vs TinyFish Fetch, for one URL."""

    url: str
    claude_web_search: BenchmarkCell
    tavily_extract: BenchmarkCell
    tinyfish_fetch: BenchmarkCell


class BenchmarkResponse(BaseModel):
    model: str
    web_content_rows: list[WebContentRow]
    generated_at: datetime
