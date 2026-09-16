"""Search execution and orchestration."""

from __future__ import annotations

import logging
from collections import defaultdict

from api.models.schemas import SearchQuery, SearchResult

logger = logging.getLogger(__name__)

# Standard search methods used in benchmarking.
SEARCH_METHODS = [
    "tavily_cli",
    "tavily_mcp",
    "search_in_prompt",
]


def execute_searches(
    fixtures: dict[str, list[SearchResult]], searches: list[SearchQuery]
) -> dict[str, list[SearchResult]]:
    """Execute or retrieve search results grouped by method.

    In the current implementation, this loads cached results from fixtures.
    In production, this could be extended to fetch live results or use
    a search service.

    Args:
        fixtures: Dictionary of fixture data loaded from api/fixtures/.
        searches: List of search queries to execute.

    Returns:
        Dictionary mapping method names to lists of SearchResult objects.
        Each method will have one result per search query.
    """
    del searches  # Query count is implicit in the fixture data.
    results_by_method: dict[str, list[SearchResult]] = defaultdict(list)

    for _fixture_name, results in fixtures.items():
        for result in results:
            results_by_method[result.method].append(result)

    # Ensure all expected methods are present in the output.
    for method in SEARCH_METHODS:
        if method not in results_by_method:
            logger.debug(f"No fixture results found for method: {method}")
            results_by_method[method] = []

    logger.info(
        f"Executed searches with fixture data: {len(results_by_method)} methods, "
        f"{sum(len(v) for v in results_by_method.values())} total results"
    )

    return dict(results_by_method)
