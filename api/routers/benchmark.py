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


@router.get("/benchmark", response_model=BenchmarkResponse)
async def get_benchmark(
    model: str = Query(
        "claude-sonnet-5",
        description="Claude model to use for tokenization and cost calculation",
    ),
) -> BenchmarkResponse:
    """Get benchmark comparison for all search methods.

    Loads fixture data (cached search results), calculates token counts
    and costs for each method, and returns two comparison groups:
    - Tokens comparison
    - Cost comparison

    Args:
        model: The Claude model to use (default: claude-sonnet-5).
            Must be one of: claude-haiku-4-5, claude-sonnet-5, claude-opus-5.

    Returns:
        BenchmarkResponse containing two comparison groups with results
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

            method_metrics[method] = {"tokens": total_tokens, "cost": total_cost}
            method_has_data[method] = len(results) > 0
            logger.info(f"Method {method}: {total_tokens} tokens, ${total_cost:.6f} cost")

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
                title="Token Count Comparison",
                caption="Total tokens used across all search results for each method",
                items=items,
                winner_index=0,
            ),
            BenchmarkGroup(
                title="Cost Comparison",
                caption=f"Total cost in USD for {len(searches)} searches using {model}",
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
