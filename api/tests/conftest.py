"""Pytest configuration and shared fixtures for Benchmark Tavily API tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.models.schemas import SearchQuery, SearchResult


@pytest.fixture
def fixture_mock_searches() -> list[SearchQuery]:
    """Create mock search queries for testing.

    Returns:
        List of 3 SearchQuery objects for testing.
    """
    return [
        SearchQuery(
            query="latest release of the package uv",
            note="Find current version number of uv package manager",
            successfuly_return_includes=["uv", "0."],
        ),
        SearchQuery(
            query="current stable version of Svelte compiler",
            note="Find the latest stable Svelte compiler version",
            successfuly_return_includes=["svelte", "@sveltejs/svelte"],
        ),
        SearchQuery(
            query="Tavily extract API endpoint return",
            note="Document structure and response format of Tavily extract API",
            successfuly_return_includes=["extract", "api"],
        ),
    ]


@pytest.fixture
def fixture_mock_results() -> dict[str, list[SearchResult]]:
    """Create mock search results for testing.

    Returns:
        Dictionary mapping fixture names to lists of SearchResult objects.
        Contains results from all three methods: tavily_cli, tavily_mcp,
        and search_in_prompt.
    """
    return {
        "fixture_1": [
            SearchResult(
                method="tavily_cli",
                raw_response="Tavily CLI result for query 1. This is a sample response with "
                "multiple lines of content to test token calculation. "
                "The uv package manager is a modern Python package installer.",
                timestamp=datetime.now(UTC).isoformat(),
            ),
            SearchResult(
                method="tavily_mcp",
                raw_response="Tavily MCP result for query 1. MCP provides search results "
                "through a structured protocol. Results include metadata and ranking. "
                "uv is version 0.5.0 currently.",
                timestamp=datetime.now(UTC).isoformat(),
            ),
            SearchResult(
                method="search_in_prompt",
                raw_response="Search-in-Prompt result for query 1. This method embeds "
                "search directly in the prompt to Claude. Results are shorter. "
                "uv 0.5.0",
                timestamp=datetime.now(UTC).isoformat(),
            ),
        ],
        "fixture_2": [
            SearchResult(
                method="tavily_cli",
                raw_response="Tavily CLI result for query 2. Svelte compiler is a tool for "
                "compiling Svelte components. The latest stable version is 5.0.0. "
                "Svelte provides reactive web applications.",
                timestamp=datetime.now(UTC).isoformat(),
            ),
            SearchResult(
                method="tavily_mcp",
                raw_response="Tavily MCP result for query 2. Svelte version 5.0.0 is the "
                "latest stable release. @sveltejs/svelte is the main package. "
                "Documentation is available on npm.",
                timestamp=datetime.now(UTC).isoformat(),
            ),
            SearchResult(
                method="search_in_prompt",
                raw_response="Search-in-Prompt result for query 2. Svelte 5.0.0 stable. "
                "@sveltejs/svelte package.",
                timestamp=datetime.now(UTC).isoformat(),
            ),
        ],
        "fixture_3": [
            SearchResult(
                method="tavily_cli",
                raw_response="Tavily CLI result for query 3. The extract API endpoint of "
                "Tavily returns structured JSON with extracted information from web pages. "
                "The response includes title, content, and metadata fields.",
                timestamp=datetime.now(UTC).isoformat(),
            ),
            SearchResult(
                method="tavily_mcp",
                raw_response="Tavily MCP result for query 3. Extract API endpoint structure: "
                "{url: string, title: string, content: string, raw_content: string, "
                "extracted_content: string}. Response format includes metadata.",
                timestamp=datetime.now(UTC).isoformat(),
            ),
            SearchResult(
                method="search_in_prompt",
                raw_response="Search-in-Prompt result for query 3. Tavily extract endpoint. "
                "API returns JSON with content extraction.",
                timestamp=datetime.now(UTC).isoformat(),
            ),
        ],
    }


@pytest.fixture
def fixture_token_calculator_mock() -> Any:
    """Create a mock token calculator for testing.

    This fixture patches the token calculator functions to return
    predictable values for testing without requiring the tiktoken library
    to actually tokenize text.

    Yields:
        A dict of the two MagicMock objects backing the patched functions.
    """
    with patch("api.services.token_calculator.calculate_tokens") as mock_calc:
        with patch("api.services.token_calculator.calculate_cost") as mock_cost:

            def calculate_tokens_side_effect(text: str, model: str) -> int:
                del model
                return max(1, len(text) // 4)

            def calculate_cost_side_effect(tokens: int, model: str) -> float:
                if model == "claude-haiku-4-5":
                    return round((tokens / 1_000_000) * 1.00, 6)
                elif model == "claude-sonnet-5":
                    return round((tokens / 1_000_000) * 2.00, 6)
                elif model == "claude-opus-5":
                    return round((tokens / 1_000_000) * 5.00, 6)
                else:
                    raise ValueError(f"Unknown model: {model}")

            mock_calc.side_effect = calculate_tokens_side_effect
            mock_cost.side_effect = calculate_cost_side_effect

            yield {"calculate_tokens": mock_calc, "calculate_cost": mock_cost}


@pytest.fixture
def app_client() -> TestClient:
    """Create a TestClient for the FastAPI application.

    Returns:
        A FastAPI TestClient configured for the benchmark app.
    """
    return TestClient(app)


@pytest.fixture
def mock_load_searches(fixture_mock_searches: list[SearchQuery]) -> Any:
    """Fixture to mock load_searches function.

    Args:
        fixture_mock_searches: The mock searches fixture.

    Yields:
        A patched version of load_searches that returns mock data.
    """
    with patch(
        "api.routers.benchmark.load_searches",
        return_value=fixture_mock_searches,
    ) as mock:
        yield mock


@pytest.fixture
def mock_load_fixtures(fixture_mock_results: dict[str, list[SearchResult]]) -> Any:
    """Fixture to mock load_fixtures function.

    Args:
        fixture_mock_results: The mock results fixture.

    Yields:
        A patched version of load_fixtures that returns mock data.
    """
    with patch(
        "api.routers.benchmark.load_fixtures",
        return_value=fixture_mock_results,
    ) as mock:
        yield mock


@pytest.fixture
def mock_calculate_tokens_and_cost() -> Any:
    """Fixture to mock calculate_tokens_and_cost function.

    This calculates based on text length to provide predictable results.

    Yields:
        A patched version of calculate_tokens_and_cost that returns
        predictable mock values.
    """

    def mock_impl(text: str, model: str) -> tuple[int, float]:
        """Mock implementation that calculates based on text length."""
        tokens = max(1, len(text) // 4)

        rates = {
            "claude-haiku-4-5": 1.00,
            "claude-sonnet-5": 2.00,
            "claude-opus-5": 5.00,
        }

        if model not in rates:
            raise ValueError(f"Unknown model: {model}")

        cost = round((tokens / 1_000_000) * rates[model], 6)
        return tokens, cost

    with patch(
        "api.routers.benchmark.calculate_tokens_and_cost",
        side_effect=mock_impl,
    ) as mock:
        yield mock
