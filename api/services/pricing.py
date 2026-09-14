"""Reference model + published per-token price used to turn a token count
into a $ estimate for every benchmark cell — see specs/tavily-benchmark-app.md §6.

Source: https://platform.claude.com/docs/en/about-claude/pricing — Claude
Sonnet 5 standard pricing as of September 2026: $2/1M input tokens, $10/1M
output tokens. This app prices every cell as if its response payload were
fed to the model as INPUT (the scenario the tokens/price columns model —
"what would it cost to hand this tool's result to an LLM"), so the input
rate applies. Re-verify this figure against the source above before relying
on it for anything beyond relative comparison between methods.
"""

from __future__ import annotations

REFERENCE_MODEL = "claude-sonnet-5"
PRICE_PER_MILLION_TOKENS_USD = 2.0


def price_for_tokens(tokens: int) -> float:
    return tokens / 1_000_000 * PRICE_PER_MILLION_TOKENS_USD
