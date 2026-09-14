"""Loads recorded response fixtures for both tables and turns them into
BenchmarkResponse rows via the shared tokenizer/pricing pipeline. This is
the ONLY data path used by the served app and by CI/Docker/Playwright —
there is no live request-time path (see specs/tavily-benchmark-app.md §4).

Fixtures are keyed positionally: fixture file `N.json` under each provider
directory corresponds to the Nth (0-indexed) entry in the matching
inputs.yaml list. This mirrors how scripts/record_benchmark_fixtures.py
writes them.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from api.models.schemas import BenchmarkCell, BenchmarkResponse, ToolCallRow, WebContentRow
from api.services import benchmark_inputs
from api.services.pricing import REFERENCE_MODEL, price_for_tokens
from api.services.tokenizer import count_tokens

HERE = Path(__file__).resolve().parent.parent  # api/
TOOL_CALL_RAW_DIR = HERE / "fixtures" / "tool_call" / "raw"
TOOL_CALL_MCP_DIR = HERE / "fixtures" / "tool_call" / "mcp"
WEB_CONTENT_CLAUDE_DIR = HERE / "fixtures" / "web_content" / "claude_web_search"
WEB_CONTENT_EXTRACT_DIR = HERE / "fixtures" / "web_content" / "tavily_extract"


def _cell_from_fixture(directory: Path, index: int) -> BenchmarkCell:
    path = directory / f"{index}.json"
    with open(path) as f:
        recording = json.load(f)
    response_text = recording["response_text"]
    tokens = count_tokens(response_text)
    return BenchmarkCell(
        tokens=tokens,
        price_usd=price_for_tokens(tokens),
        latency_ms=recording.get("latency_ms", 0.0),
        response_bytes=recording.get("response_bytes", len(response_text.encode())),
    )


def load_tool_call_rows() -> list[ToolCallRow]:
    queries = benchmark_inputs.load_tool_call_queries()
    rows = []
    for i, q in enumerate(queries):
        rows.append(
            ToolCallRow(
                query=q.query,
                raw_tool_call=_cell_from_fixture(TOOL_CALL_RAW_DIR, i),
                mcp=_cell_from_fixture(TOOL_CALL_MCP_DIR, i),
            )
        )
    return rows


def load_web_content_rows() -> list[WebContentRow]:
    pairs = benchmark_inputs.load_web_content_pairs()
    rows = []
    for i, p in enumerate(pairs):
        rows.append(
            WebContentRow(
                url=p.url,
                question=p.question,
                claude_web_search=_cell_from_fixture(WEB_CONTENT_CLAUDE_DIR, i),
                tavily_extract=_cell_from_fixture(WEB_CONTENT_EXTRACT_DIR, i),
            )
        )
    return rows


def load_benchmark_response() -> BenchmarkResponse:
    return BenchmarkResponse(
        model=REFERENCE_MODEL,
        tool_call_rows=load_tool_call_rows(),
        web_content_rows=load_web_content_rows(),
        generated_at=datetime.now(UTC),
    )
