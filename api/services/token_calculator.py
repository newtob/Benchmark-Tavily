"""Token calculation and cost estimation utilities."""

from __future__ import annotations

import logging

import tiktoken

logger = logging.getLogger(__name__)

# Pricing rates for Claude models (USD per 1M input tokens).
# Source: Anthropic first-party API pricing (cached 2026-06-24).
RATES: dict[str, dict[str, float]] = {
    "claude-haiku-4-5": {
        "input": 1.00,
        "output": 5.00,
    },
    "claude-sonnet-5": {
        "input": 2.00,
        "output": 10.00,
    },
    "claude-opus-5": {
        "input": 5.00,
        "output": 25.00,
    },
}

# tiktoken has no Claude-specific encoding; cl100k_base is used as a
# consistent approximation across all Claude models (see specs/plan_prompt.md).
DEFAULT_ENCODING = "cl100k_base"


def calculate_tokens(text: str, model: str) -> int:
    """Calculate the number of tokens in a text string.

    Uses the tiktoken library as an approximation of token count, since
    tiktoken has no Claude-specific tokenizer. Always falls back to
    cl100k_base encoding.

    Args:
        text: The text to tokenize.
        model: The model identifier (e.g., "claude-haiku-4-5"). Unused for
            encoding selection but kept for API symmetry with calculate_cost.

    Returns:
        The number of tokens in the text.
    """
    del model  # tiktoken has no Claude encodings; always use the fallback.
    encoding = tiktoken.get_encoding(DEFAULT_ENCODING)
    return len(encoding.encode(text))


def calculate_cost(tokens: int, model: str) -> float:
    """Calculate the cost in USD for a given number of tokens.

    Assumes tokens are input tokens (most common case for benchmarking
    search results). Uses pricing rates from RATES dict.

    Args:
        tokens: Number of tokens.
        model: The model identifier (e.g., "claude-haiku-4-5").

    Returns:
        The cost in USD. Rounds to 6 decimal places for precision.

    Raises:
        ValueError: If the model is not in the RATES dictionary.
    """
    if model not in RATES:
        raise ValueError(f"Unknown model: {model}. Available models: {list(RATES.keys())}")

    rate = RATES[model]["input"]
    cost = (tokens / 1_000_000) * rate
    return round(cost, 6)


def calculate_tokens_and_cost(text: str, model: str) -> tuple[int, float]:
    """Calculate tokens and cost for a given text and model.

    Args:
        text: The text to tokenize.
        model: The model identifier (e.g., "claude-haiku-4-5").

    Returns:
        A tuple of (tokens, cost_usd).

    Raises:
        ValueError: If the model is not in the RATES dictionary.
    """
    tokens = calculate_tokens(text, model)
    cost = calculate_cost(tokens, model)
    return tokens, cost
