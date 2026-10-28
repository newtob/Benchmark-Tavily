"""Unit + router tests for the Tavily Benchmark app's backend.
See specs/tavily-benchmark-app.md §11."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from api.services.pricing import PRICE_PER_MILLION_TOKENS_USD, price_for_tokens
from api.services.tokenizer import count_tokens

client = TestClient(app)


def test_count_tokens_is_deterministic() -> None:
    text = "return the latest release for the package `uv`"
    assert count_tokens(text) == count_tokens(text)
    assert count_tokens(text) > 0


def test_count_tokens_empty_string_is_zero() -> None:
    assert count_tokens("") == 0


def test_price_for_tokens() -> None:
    assert price_for_tokens(1_000_000) == PRICE_PER_MILLION_TOKENS_USD
    assert price_for_tokens(0) == 0.0


def test_healthz() -> None:
    response = client.get("/api/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_benchmark_response_shape() -> None:
    response = client.get("/api/benchmark")
    assert response.status_code == 200
    body = response.json()

    assert body["model"]
    assert len(body["web_content_rows"]) == 10

    for row in body["web_content_rows"]:
        assert row["url"]
        for cell_key in ("claude_web_search", "tavily_extract", "tinyfish_fetch"):
            cell = row[cell_key]
            assert cell["tokens"] > 0
            assert cell["price_usd"] >= 0
