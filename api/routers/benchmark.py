"""Benchmark comparison endpoint."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query

from api.models.schemas import (
    BenchmarkGroup,
    BenchmarkItem,
    BenchmarkResponse,
)
from api.services import (
    calculate_tokens_and_cost,
    execute_searches,
    load_fixtures,
    load_searches,
)
from api.services.token_calculator import RATES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["benchmark"])

# Displayed costs project a single search's average cost out to this many
# searches, rather than showing the raw total across the small fixed sample
# in searches.yaml.
ESTIMATE_SEARCH_COUNT = 1000


@router.get("/benchmark", response_model=BenchmarkResponse)
async def get_benchmark(
    model: str = Query(
        "claude-sonnet-5",
        description="Claude model to use for tokenization and cost calculation",
    ),
) -> BenchmarkResponse:
    """Get benchmark comparison for all search methods.

    Loads fixture data (cached search results), calculates each method's
    average tokens/cost per search, and projects that out to
    ``ESTIMATE_SEARCH_COUNT`` searches, returning a single cost comparison
    group.

    Args:
        model: The Claude model to use (default: claude-sonnet-5).
            Must be one of: claude-haiku-4-5, claude-sonnet-5, claude-opus-5.

    Returns:
        BenchmarkResponse containing one cost comparison group with results
        for all search methods.

    Raises:
        HTTPException: If model is not supported or fixtures cannot be loaded.
    """
    if model not in RATES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported model: {model}. Available models: {list(RATES.keys())}",
        )

    try:
        searches = load_searches()
        fixtures = load_fixtures()
        results_by_method = execute_searches(fixtures, searches)

        method_metrics: dict[str, dict[str, int | float]] = {}
        method_has_data: dict[str, bool] = {}
        for method, results in results_by_method.items():
            total_tokens = 0
            total_cost = 0.0
            for result in results:
                tokens, cost = calculate_tokens_and_cost(result.raw_response, model)
                total_tokens += tokens
                total_cost += cost

            # Project the average per-search tokens/cost out to
            # ESTIMATE_SEARCH_COUNT searches, rather than showing the raw
            # total across the small fixed sample in searches.yaml.
            if results:
                avg_tokens = total_tokens / len(results)
                avg_cost = total_cost / len(results)
            else:
                avg_tokens = 0.0
                avg_cost = 0.0

            estimated_tokens = avg_tokens * ESTIMATE_SEARCH_COUNT
            estimated_cost = avg_cost * ESTIMATE_SEARCH_COUNT

            method_metrics[method] = {"tokens": estimated_tokens, "cost": estimated_cost}
            method_has_data[method] = len(results) > 0
            logger.info(
                f"Method {method}: {estimated_tokens:.0f} tokens, ${estimated_cost:.6f} cost "
                f"(estimated for {ESTIMATE_SEARCH_COUNT} searches)"
            )

        # Sort methods by cost (then tokens as a tiebreaker) to find the winner.
        # A method with no recorded results at all (e.g. missing fixtures)
        # sorts last regardless of its zero cost/tokens - it hasn't "won" by
        # being cheap, it just has no data to show.
        sorted_methods = sorted(
            method_metrics.items(),
            key=lambda entry: (
                not method_has_data[entry[0]],
                entry[1]["cost"],
                entry[1]["tokens"],
            ),
        )

        items = [
            BenchmarkItem(
                label=method.replace("_", " ").title(),
                method=method,
                tokens=int(metrics["tokens"]),
                cost_usd=float(metrics["cost"]),
            )
            for method, metrics in sorted_methods
        ]

        groups = [
            BenchmarkGroup(
                title="Cost Comparison",
                caption=(
                    f"Estimated cost in USD for {ESTIMATE_SEARCH_COUNT} searches using "
                    f"{model}, projected from each method's average cost per search"
                ),
                items=items,
                winner_index=0,
            ),
        ]

        return BenchmarkResponse(
            model=model,
            groups=groups,
            generated_at=datetime.now(UTC),
        )

    except FileNotFoundError as e:
        logger.error(f"Missing required files: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Benchmark data unavailable: {e}",
        ) from e

    except Exception as e:
        logger.error(f"Error generating benchmark: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error while generating benchmark",
        ) from e
