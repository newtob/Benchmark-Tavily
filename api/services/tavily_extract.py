"""Table 2, "Tavily Extract" column: calls Tavily's REST `extract` endpoint
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

EXTRACT_URL = "https://api.tavily.com/extract"


@dataclass(frozen=True)
class ExtractRecording:
    url: str
    response_text: str  # extracted page content, as text — tokenized by tokenizer.py
    latency_ms: float
    response_bytes: int


def invoke(url: str, *, api_key: str, timeout_s: float = 30) -> ExtractRecording:
    """Call Tavily's extract endpoint directly. Live-mode only."""
    started = time.monotonic()
    response = httpx.post(
        EXTRACT_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"urls": [url], "extract_depth": "basic", "format": "markdown"},
        timeout=timeout_s,
    )
    response.raise_for_status()
    latency_ms = (time.monotonic() - started) * 1000
    return parse_response(url, response.json(), latency_ms=latency_ms)


def parse_response(url: str, raw_json: dict[str, Any], *, latency_ms: float) -> ExtractRecording:
    results = raw_json.get("results", [])
    # Concatenate every returned result's raw content — normally one entry
    # for a single-URL request, but stay robust to Tavily returning more.
    response_text = (
        "\n\n".join(r.get("raw_content") or r.get("content") or "" for r in results) or ""
    )
    if not response_text:
        # Fall back to the whole payload so a malformed/empty extract still
        # produces a non-zero, inspectable token count rather than silently
        # scoring as free.
        import json as _json

        response_text = _json.dumps(raw_json)
    return ExtractRecording(
        url=url,
        response_text=response_text,
        latency_ms=latency_ms,
        response_bytes=len(response_text.encode()),
    )
