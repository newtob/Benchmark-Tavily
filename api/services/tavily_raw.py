"""Table 1, "Raw tool call" column: calls Tavily's REST `search` endpoint
directly over HTTP — see specs/tavily-benchmark-app.md §4/§14.

Only `invoke()` is called live, and only by scripts/record_benchmark_fixtures.py
(when TAVILY_LIVE=1). The served app always replays recorded fixtures via
fixtures.py; parse_response() is shared so live-recorded and replayed data
are shaped identically.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

SEARCH_URL = "https://api.tavily.com/search"


@dataclass(frozen=True)
class RawToolCallRecording:
    query: str
    response_text: str  # the raw JSON response, as text — tokenized by tokenizer.py
    latency_ms: float
    response_bytes: int


def invoke(query: str, *, api_key: str, timeout_s: float = 30) -> RawToolCallRecording:
    """Call Tavily's search endpoint directly. Live-mode only."""
    started = time.monotonic()
    response = httpx.post(
        SEARCH_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"query": query, "search_depth": "basic", "max_results": 5},
        timeout=timeout_s,
    )
    response.raise_for_status()
    latency_ms = (time.monotonic() - started) * 1000
    return parse_response(query, response.json(), latency_ms=latency_ms)


def parse_response(
    query: str, raw_json: dict[str, Any], *, latency_ms: float
) -> RawToolCallRecording:
    import json as _json

    response_text = _json.dumps(raw_json)
    return RawToolCallRecording(
        query=query,
        response_text=response_text,
        latency_ms=latency_ms,
        response_bytes=len(response_text.encode()),
    )
