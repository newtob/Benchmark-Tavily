"""Table 2, "TinyFish Fetch" column: runs `tinyfish fetch content get` for the
URL (markdown) — the counterpart of tavily_extract.py.

Only `invoke()` is called live, and only by scripts/record_benchmark_fixtures.py.
The served app always replays recorded fixtures via fixtures.py;
parse_response() is shared so live-recorded and replayed data are shaped
identically.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TinyFishFetchRecording:
    url: str
    response_text: str  # extracted page content, as text — tokenized by tokenizer.py
    latency_ms: float
    response_bytes: int


async def run_cli(*args: str, api_key: str, timeout_s: float) -> tuple[str, float]:
    """Run `tinyfish <args>`; return (stdout, wall-clock latency in ms)."""
    started = time.monotonic()
    proc = await asyncio.create_subprocess_exec(
        "tinyfish",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "TINYFISH_API_KEY": api_key},
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except TimeoutError:
        proc.kill()
        raise
    latency_ms = (time.monotonic() - started) * 1000
    if proc.returncode != 0:
        raise RuntimeError(f"tinyfish {' '.join(args[:2])} failed: {stderr.decode()[:500]}")
    return stdout.decode(), latency_ms


async def invoke(url: str, *, api_key: str, timeout_s: float = 90) -> TinyFishFetchRecording:
    """Fetch a URL's content via the TinyFish CLI. Live-mode only."""
    started = time.monotonic()
    stdout, _ = await run_cli(
        "fetch", "content", "get", url, "--format", "markdown", api_key=api_key, timeout_s=timeout_s
    )
    latency_ms = (time.monotonic() - started) * 1000
    return parse_response(url, json.loads(stdout), latency_ms=latency_ms)


def parse_response(
    url: str, raw_json: dict[str, Any], *, latency_ms: float
) -> TinyFishFetchRecording:
    results = raw_json.get("results", [])
    # Concatenate every returned result's text — normally one entry for a
    # single-URL request, but stay robust to more.
    response_text = "\n\n".join(str(r.get("text") or "") for r in results)
    if not response_text.strip():
        # Fall back to the whole payload (incl. `errors[]`) so a failed/empty
        # fetch yields a non-zero, inspectable token count rather than scoring
        # as free.
        response_text = json.dumps(raw_json)
    return TinyFishFetchRecording(
        url=url,
        response_text=response_text,
        latency_ms=latency_ms,
        response_bytes=len(response_text.encode()),
    )
