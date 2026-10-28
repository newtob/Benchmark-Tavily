"""Offline unit tests for the TinyFish services' shared parse_response()
functions — the same code path live recording and fixture replay rely on.
See specs/tavily-benchmark-app.md §11."""

from __future__ import annotations

from api.services import tinyfish_fetch


def test_fetch_parse_response_joins_result_text() -> None:
    raw = {"results": [{"text": "# Title"}, {"text": "body"}], "errors": []}
    rec = tinyfish_fetch.parse_response("https://x", raw, latency_ms=1.0)
    assert rec.response_text == "# Title\n\nbody"


def test_fetch_parse_response_falls_back_to_payload_on_error() -> None:
    raw = {"results": [], "errors": [{"url": "https://x", "error": "timeout"}]}
    rec = tinyfish_fetch.parse_response("https://x", raw, latency_ms=1.0)
    # A failed fetch must stay inspectable and non-zero, never score as free.
    assert "timeout" in rec.response_text
    assert rec.response_bytes > 0
