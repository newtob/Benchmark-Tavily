"""Loads recorded response fixtures for the page-load comparison and turns them into
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

from api.models.schemas import BenchmarkCell, BenchmarkResponse, WebContentRow
from api.services import benchmark_inputs
from api.services.pricing import REFERENCE_MODEL, price_for_tokens
from api.services.tokenizer import count_tokens

HERE = Path(__file__).resolve().parent.parent  # api/
WEB_CONTENT_CLAUDE_DIR = HERE / "fixtures" / "web_content" / "claude_web_search"
WEB_CONTENT_EXTRACT_DIR = HERE / "fixtures" / "web_content" / "tavily_extract"
WEB_CONTENT_TINYFISH_FETCH_DIR = HERE / "fixtures" / "web_content" / "tinyfish_fetch"


def _cell_from_fixture(directory: Path, index: int) -> BenchmarkCell:
    path = directory / f"{index}.json"
    with open(path) as f:
        recording = json.load(f)
    response_text = recording["response_text"]
    measured = recording.get("search_ingest_tokens")
    if measured:
        # Claude column: tokens the model really ingested from WebSearch,
        # not the length of its final answer.
        tokens, source = int(measured), "claude_usage_measured"
    else:
        tokens, source = count_tokens(response_text), "tiktoken_estimate"
    return BenchmarkCell(
        tokens=tokens,
        tokens_source=source,
        price_usd=price_for_tokens(tokens),
        latency_ms=recording.get("latency_ms", 0.0),
        response_bytes=recording.get("response_bytes", len(response_text.encode())),
    )


def load_web_content_rows() -> list[WebContentRow]:
    pairs = benchmark_inputs.load_web_content_pages()
    rows = []
    for i, p in enumerate(pairs):
        rows.append(
            WebContentRow(
                url=p.url,
                claude_web_search=_cell_from_fixture(WEB_CONTENT_CLAUDE_DIR, i),
                tavily_extract=_cell_from_fixture(WEB_CONTENT_EXTRACT_DIR, i),
                tinyfish_fetch=_cell_from_fixture(WEB_CONTENT_TINYFISH_FETCH_DIR, i),
            )
        )
    return rows


def load_benchmark_response() -> BenchmarkResponse:
    return BenchmarkResponse(
        model=REFERENCE_MODEL,
        web_content_rows=load_web_content_rows(),
        generated_at=datetime.now(UTC),
    )
