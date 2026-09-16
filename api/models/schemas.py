"""Pydantic models for request/response contracts."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Search query configuration.

    Attributes:
        query: The search query string.
        note: A note explaining the purpose of the query.
        successfuly_return_includes: List of strings that should appear
            in successful search results.
    """

    query: str
    note: str
    successfuly_return_includes: list[str]


class SearchResult(BaseModel):
    """Result from a search method.

    Attributes:
        method: Name of the search method (e.g., "tavily_cli", "tavily_mcp",
            "search_in_prompt").
        raw_response: The raw response from the search method.
        timestamp: ISO 8601 timestamp of when the search was performed.
    """

    method: str
    raw_response: str
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class BenchmarkItem(BaseModel):
    """Single benchmark measurement.

    Attributes:
        label: Display label for this measurement (e.g., method name).
        method: The search method identifier.
        tokens: Number of tokens used.
        cost_usd: Cost in USD for this method using the specified model.
    """

    label: str
    method: str
    tokens: int
    cost_usd: float


class BenchmarkGroup(BaseModel):
    """A group of benchmark items for comparison.

    Attributes:
        title: Title of the benchmark group.
        caption: Description of what is being compared.
        items: List of benchmark items (one per method, typically 3 items).
        winner_index: Index of the item with the lowest cost
            (tokens as tiebreaker).
    """

    title: str
    caption: str
    items: list[BenchmarkItem]
    winner_index: int


class BenchmarkResponse(BaseModel):
    """Response containing benchmark comparison groups.

    Attributes:
        model: The Claude model used for tokenization
            (e.g., "claude-haiku-4-5").
        groups: List of comparison groups. Contains 2 groups:
            one for token counts and one for cost comparisons.
        generated_at: ISO 8601 timestamp of when this response was generated.
    """

    model: str
    groups: list[BenchmarkGroup]
    generated_at: datetime
