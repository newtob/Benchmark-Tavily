"""Tests for token calculation and cost estimation."""

from __future__ import annotations

import pytest

from api.services.token_calculator import (
    RATES,
    calculate_cost,
    calculate_tokens,
    calculate_tokens_and_cost,
)


class TestCalculateTokens:
    """Tests for the calculate_tokens function."""

    def test_calculate_tokens_returns_int(self) -> None:
        """Verify that calculate_tokens returns an integer.

        The function should return token count as an int, always > 0
        for non-empty text.
        """
        result = calculate_tokens("Hello world", "claude-haiku-4-5")
        assert isinstance(result, int)
        assert result > 0

    def test_calculate_tokens_with_empty_text(self) -> None:
        """Test token calculation with empty string.

        Empty text should result in 0 tokens.
        """
        result = calculate_tokens("", "claude-haiku-4-5")
        assert isinstance(result, int)
        assert result == 0

    def test_calculate_tokens_with_long_text(self) -> None:
        """Verify that longer text produces more tokens (monotonic).

        Token count should be monotonically increasing with text length.
        """
        short_text = "Hello"
        long_text = "Hello world " * 100  # Much longer text

        short_tokens = calculate_tokens(short_text, "claude-haiku-4-5")
        long_tokens = calculate_tokens(long_text, "claude-haiku-4-5")

        assert long_tokens > short_tokens, (
            f"Longer text should have more tokens. " f"Short: {short_tokens}, Long: {long_tokens}"
        )

    def test_calculate_tokens_with_different_models(self) -> None:
        """Test token calculation works with different models.

        All supported models should produce valid token counts.
        """
        text = "This is a test string for tokenization"
        for model in RATES.keys():
            result = calculate_tokens(text, model)
            assert isinstance(result, int)
            assert result > 0

    def test_calculate_tokens_fallback_encoding(self) -> None:
        """Test token calculation with model that uses fallback encoding.

        When a model is not found in tiktoken, it should fall back to
        cl100k_base encoding and still produce valid results.
        """
        # Use a model name that likely won't be in tiktoken's registry
        # but should fall back to default encoding
        result = calculate_tokens("test", "gpt-4")
        assert isinstance(result, int)
        assert result > 0


class TestCalculateCost:
    """Tests for the calculate_cost function."""

    def test_calculate_cost_returns_float(self) -> None:
        """Verify that calculate_cost returns a float.

        Cost should always be a float value representing USD amount.
        """
        result = calculate_cost(1000, "claude-haiku-4-5")
        assert isinstance(result, float)

    def test_calculate_cost_zero_for_empty_text(self) -> None:
        """Test cost calculation for zero tokens.

        Zero tokens should result in $0 cost.
        """
        result = calculate_cost(0, "claude-haiku-4-5")
        assert result == 0.0

    def test_calculate_cost_haiku_4_5(self) -> None:
        """Test cost calculation at Haiku 4.5 rate.

        Haiku 4.5 should be the cheapest model.
        """
        tokens = 1_000_000  # 1M tokens
        result = calculate_cost(tokens, "claude-haiku-4-5")

        # Haiku input rate is $1.00 per 1M tokens
        expected = 1.00
        assert (
            result == expected
        ), f"Expected ${expected} for 1M tokens at Haiku rate, got ${result}"

    def test_calculate_cost_sonnet_5(self) -> None:
        """Test cost calculation at Sonnet 5 rate.

        Sonnet should be more expensive than Haiku but cheaper than Opus.
        """
        tokens = 1_000_000  # 1M tokens
        result = calculate_cost(tokens, "claude-sonnet-5")

        # Sonnet input rate is $2.00 per 1M tokens
        expected = 2.00
        assert (
            result == expected
        ), f"Expected ${expected} for 1M tokens at Sonnet rate, got ${result}"

    def test_calculate_cost_opus_5(self) -> None:
        """Test cost calculation at Opus 5 rate.

        Opus should be the most expensive model.
        """
        tokens = 1_000_000  # 1M tokens
        result = calculate_cost(tokens, "claude-opus-5")

        # Opus input rate is $5.00 per 1M tokens
        expected = 5.00
        assert result == expected, f"Expected ${expected} for 1M tokens at Opus rate, got ${result}"

    def test_calculate_cost_partial_tokens(self) -> None:
        """Test cost calculation with partial token amounts.

        Should correctly calculate cost for token amounts less than 1M.
        """
        tokens = 100_000  # 0.1M tokens
        result = calculate_cost(tokens, "claude-haiku-4-5")

        # Haiku: (100,000 / 1,000,000) * 1.00 = 0.10
        expected = 0.10
        assert result == expected

    def test_rate_lookup_for_unknown_model(self) -> None:
        """Test that unknown model raises ValueError.

        Calling calculate_cost with an unsupported model should
        raise ValueError with a helpful message.
        """
        with pytest.raises(ValueError, match="Unknown model"):
            calculate_cost(1000, "unknown-model-xyz")

    def test_cost_increases_with_tokens(self) -> None:
        """Verify that cost increases monotonically with token count.

        More tokens should always result in higher cost.
        """
        low_cost = calculate_cost(1000, "claude-haiku-4-5")
        high_cost = calculate_cost(10000, "claude-haiku-4-5")

        assert high_cost > low_cost, (
            f"Higher token count should cost more. "
            f"1k tokens: ${low_cost}, 10k tokens: ${high_cost}"
        )

    def test_cost_scales_with_model_rate(self) -> None:
        """Verify that more expensive models have higher costs.

        For the same token count, Sonnet > Haiku and Opus > Sonnet.
        """
        tokens = 1_000_000

        haiku_cost = calculate_cost(tokens, "claude-haiku-4-5")
        sonnet_cost = calculate_cost(tokens, "claude-sonnet-5")
        opus_cost = calculate_cost(tokens, "claude-opus-5")

        assert haiku_cost < sonnet_cost < opus_cost, (
            f"Model costs should scale: Haiku (${haiku_cost}) < "
            f"Sonnet (${sonnet_cost}) < Opus (${opus_cost})"
        )


class TestCalculateTokensAndCost:
    """Tests for the combined calculate_tokens_and_cost function."""

    def test_calculate_tokens_and_cost_returns_tuple(self) -> None:
        """Verify that calculate_tokens_and_cost returns a (int, float) tuple.

        Returns:
            - First element (int): token count
            - Second element (float): cost in USD
        """
        result = calculate_tokens_and_cost("Hello world", "claude-haiku-4-5")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], int)
        assert isinstance(result[1], float)

    def test_calculate_tokens_and_cost_consistency(self) -> None:
        """Verify that combined function is consistent with separate calls.

        The cost returned should match what calculate_cost would return
        for the same token count.
        """
        text = "This is a test string for consistency checking"
        model = "claude-haiku-4-5"

        tokens, cost = calculate_tokens_and_cost(text, model)
        separate_tokens = calculate_tokens(text, model)
        separate_cost = calculate_cost(tokens, model)

        assert tokens == separate_tokens
        assert cost == separate_cost

    def test_calculate_tokens_and_cost_with_empty_text(self) -> None:
        """Test combined calculation with empty text.

        Empty text should result in 0 tokens and $0 cost.
        """
        tokens, cost = calculate_tokens_and_cost("", "claude-haiku-4-5")
        assert tokens == 0
        assert cost == 0.0

    def test_calculate_tokens_and_cost_different_models(self) -> None:
        """Test combined calculation works with all supported models.

        Should produce valid results for all models in RATES dict.
        """
        text = "Test text for all models"

        for model in RATES.keys():
            tokens, cost = calculate_tokens_and_cost(text, model)
            assert isinstance(tokens, int)
            assert isinstance(cost, float)
            assert tokens > 0
            assert cost > 0

    def test_calculate_tokens_and_cost_with_unknown_model(self) -> None:
        """Test combined calculation with unknown model raises ValueError.

        Should raise ValueError consistent with calculate_cost behavior.
        """
        with pytest.raises(ValueError, match="Unknown model"):
            calculate_tokens_and_cost("text", "unknown-model")

    def test_cost_ratio_matches_model_rates(self) -> None:
        """Verify that cost ratios between models match RATES.

        For the same text/token count, cost ratios should match the
        rate ratios between models.
        """
        text = "Standard test text for rate comparison"

        _, haiku_cost = calculate_tokens_and_cost(text, "claude-haiku-4-5")
        _, sonnet_cost = calculate_tokens_and_cost(text, "claude-sonnet-5")

        # The ratio of costs should equal ratio of rates
        haiku_rate = RATES["claude-haiku-4-5"]["input"]
        sonnet_rate = RATES["claude-sonnet-5"]["input"]
        rate_ratio = sonnet_rate / haiku_rate

        # Allow small floating point error
        cost_ratio = sonnet_cost / haiku_cost
        assert (
            abs(cost_ratio - rate_ratio) < 0.2
        ), f"Cost ratio ({cost_ratio}) should match rate ratio ({rate_ratio})"
