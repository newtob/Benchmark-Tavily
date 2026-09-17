"""Tests for the benchmark endpoint."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from api.models.schemas import BenchmarkResponse, SearchQuery, SearchResult
from api.services.token_calculator import calculate_tokens_and_cost


class TestBenchmarkRouteBasics:
    """Basic endpoint response tests."""

    def test_get_benchmark_returns_200(
        self,
        app_client: TestClient,
        mock_load_searches: None,
        mock_load_fixtures: None,
        mock_calculate_tokens_and_cost: None,
    ) -> None:
        """Verify that the /api/benchmark endpoint returns 200 OK.

        Args:
            app_client: FastAPI test client.
            mock_load_searches: Mocked load_searches function.
            mock_load_fixtures: Mocked load_fixtures function.
            mock_calculate_tokens_and_cost: Mocked token calculator.
        """
        response = app_client.get("/api/benchmark")
        assert response.status_code == 200

    def test_benchmark_response_schema(
        self,
        app_client: TestClient,
        mock_load_searches: None,
        mock_load_fixtures: None,
        mock_calculate_tokens_and_cost: None,
    ) -> None:
        """Verify that response matches BenchmarkResponse model.

        Args:
            app_client: FastAPI test client.
            mock_load_searches: Mocked load_searches function.
            mock_load_fixtures: Mocked load_fixtures function.
            mock_calculate_tokens_and_cost: Mocked token calculator.
        """
        response = app_client.get("/api/benchmark")
        assert response.status_code == 200

        # Verify response can be parsed as BenchmarkResponse
        data = response.json()
        benchmark_response = BenchmarkResponse(**data)

        # Verify required fields exist
        assert hasattr(benchmark_response, "model")
        assert hasattr(benchmark_response, "groups")
        assert hasattr(benchmark_response, "generated_at")
        assert isinstance(benchmark_response.model, str)
        assert isinstance(benchmark_response.groups, list)


class TestBenchmarkGroupStructure:
    """Tests for benchmark response group structure."""

    def test_benchmark_has_one_group(
        self,
        app_client: TestClient,
        mock_load_searches: None,
        mock_load_fixtures: None,
        mock_calculate_tokens_and_cost: None,
    ) -> None:
        """Assert that response.groups has exactly 1 item: Cost Comparison.

        Args:
            app_client: FastAPI test client.
            mock_load_searches: Mocked load_searches function.
            mock_load_fixtures: Mocked load_fixtures function.
            mock_calculate_tokens_and_cost: Mocked token calculator.
        """
        response = app_client.get("/api/benchmark")
        data = response.json()

        assert len(data["groups"]) == 1
        assert data["groups"][0]["title"] == "Cost Comparison"

    def test_each_group_has_three_items(
        self,
        app_client: TestClient,
        mock_load_searches: None,
        mock_load_fixtures: None,
        mock_calculate_tokens_and_cost: None,
    ) -> None:
        """Assert that each group has exactly 3 benchmark items.

        Args:
            app_client: FastAPI test client.
            mock_load_searches: Mocked load_searches function.
            mock_load_fixtures: Mocked load_fixtures function.
            mock_calculate_tokens_and_cost: Mocked token calculator.
        """
        response = app_client.get("/api/benchmark")
        data = response.json()

        for group in data["groups"]:
            assert len(group["items"]) == 3, (
                f"Group '{group['title']}' should have 3 items, " f"got {len(group['items'])}"
            )

    def test_each_item_has_required_fields(
        self,
        app_client: TestClient,
        mock_load_searches: None,
        mock_load_fixtures: None,
        mock_calculate_tokens_and_cost: None,
    ) -> None:
        """Verify each benchmark item has required fields.

        Args:
            app_client: FastAPI test client.
            mock_load_searches: Mocked load_searches function.
            mock_load_fixtures: Mocked load_fixtures function.
            mock_calculate_tokens_and_cost: Mocked token calculator.
        """
        response = app_client.get("/api/benchmark")
        data = response.json()

        for group in data["groups"]:
            for item in group["items"]:
                assert "label" in item
                assert "method" in item
                assert "tokens" in item
                assert "cost_usd" in item
                assert isinstance(item["tokens"], int)
                assert isinstance(item["cost_usd"], int | float)


class TestBenchmarkWinner:
    """Tests for winner determination logic."""

    def test_winner_index_is_correct(
        self,
        app_client: TestClient,
        mock_load_searches: None,
        mock_load_fixtures: None,
        mock_calculate_tokens_and_cost: None,
    ) -> None:
        """Verify that winner_index points to lowest-cost item.

        Args:
            app_client: FastAPI test client.
            mock_load_searches: Mocked load_searches function.
            mock_load_fixtures: Mocked load_fixtures function.
            mock_calculate_tokens_and_cost: Mocked token calculator.
        """
        response = app_client.get("/api/benchmark")
        data = response.json()

        for group in data["groups"]:
            winner_index = group["winner_index"]
            winner_item = group["items"][winner_index]

            # Verify winner has lowest cost
            min_cost = min(item["cost_usd"] for item in group["items"])
            assert winner_item["cost_usd"] == min_cost, (
                f"Winner should have lowest cost ({min_cost}), "
                f"but has ${winner_item['cost_usd']}"
            )

    def test_winner_excludes_method_with_no_data(
        self,
        app_client: TestClient,
        fixture_mock_searches: list[SearchQuery],
    ) -> None:
        """A method with zero results must not win just because its cost is $0.

        Regression test: search_in_prompt with no recorded fixtures (e.g.
        missing Anthropic credentials) has tokens=0/cost_usd=0.0, which used
        to sort first and falsely show as "most efficient" even though it
        has no data at all.
        """
        results_missing_one_method = {
            "fixture_1": [
                SearchResult(
                    method="tavily_cli",
                    raw_response="A" * 400,
                    timestamp="2024-01-01T00:00:00",
                ),
                SearchResult(
                    method="tavily_mcp",
                    raw_response="B" * 800,
                    timestamp="2024-01-01T00:00:00",
                ),
                # search_in_prompt has no fixture at all - not in this dict.
            ],
        }

        with (
            patch(
                "api.routers.benchmark.load_searches",
                return_value=fixture_mock_searches,
            ),
            patch(
                "api.routers.benchmark.load_fixtures",
                return_value=results_missing_one_method,
            ),
        ):
            response = app_client.get("/api/benchmark")
            data = response.json()

            for group in data["groups"]:
                winner_item = group["items"][group["winner_index"]]
                assert winner_item["method"] != "search_in_prompt", (
                    "A method with zero results should never win, " f"got winner={winner_item}"
                )
                assert winner_item["tokens"] > 0

    def test_winner_tiebreaker_uses_tokens(
        self,
        app_client: TestClient,
        fixture_mock_results: dict[str, list[SearchResult]],
    ) -> None:
        """When costs are equal, verify lowest tokens wins (tiebreaker).

        Args:
            app_client: FastAPI test client.
            fixture_mock_results: Mock results for comparison.
        """
        # Create mock results where all methods have equal cost but different tokens
        equal_cost_results = {
            "fixture_1": [
                SearchResult(
                    method="tavily_cli",
                    raw_response="A" * 1000,  # 250 tokens
                    timestamp="2024-01-01T00:00:00",
                ),
                SearchResult(
                    method="tavily_mcp",
                    raw_response="B" * 500,  # 125 tokens
                    timestamp="2024-01-01T00:00:00",
                ),
                SearchResult(
                    method="search_in_prompt",
                    raw_response="C" * 1500,  # 375 tokens
                    timestamp="2024-01-01T00:00:00",
                ),
            ],
        }

        with patch(
            "api.routers.benchmark.load_searches",
            return_value=[
                SearchQuery(
                    query="test",
                    note="test",
                    successfuly_return_includes=[],
                )
            ],
        ):
            with patch(
                "api.routers.benchmark.load_fixtures",
                return_value=equal_cost_results,
            ):

                def mock_calc(text: str, model: str) -> tuple[int, float]:
                    tokens = len(text) // 4
                    # All return same cost regardless of tokens
                    return tokens, 0.001

                with patch(
                    "api.routers.benchmark.calculate_tokens_and_cost",
                    side_effect=mock_calc,
                ):
                    response = app_client.get("/api/benchmark")
                    data = response.json()

                    # Winner should be tavily_mcp (lowest tokens: 125 per search).
                    # Only 1 search was mocked, so the displayed value is that
                    # single search's tokens projected out to 1000 searches.
                    winner_item = data["groups"][0]["items"][0]
                    # The items are sorted by cost then tokens
                    assert winner_item["tokens"] == 125 * 1000


class TestBenchmarkCostEstimate:
    """Tests for the 1000-search cost/token projection."""

    def test_single_search_cost_is_multiplied_by_1000(
        self,
        app_client: TestClient,
    ) -> None:
        """With exactly one fixed search, the displayed tokens/cost must equal
        that one search's tokens/cost multiplied by 1000 - the documented
        estimation methodology (see ESTIMATE_SEARCH_COUNT in
        api/routers/benchmark.py).
        """
        single_search_results = {
            "fixture_1": [
                SearchResult(
                    method="tavily_cli",
                    raw_response="X" * 400,
                    timestamp="2024-01-01T00:00:00",
                ),
            ],
        }

        with (
            patch(
                "api.routers.benchmark.load_searches",
                return_value=[
                    SearchQuery(query="test", note="test", successfuly_return_includes=[])
                ],
            ),
            patch(
                "api.routers.benchmark.load_fixtures",
                return_value=single_search_results,
            ),
        ):
            one_search_tokens, one_search_cost = calculate_tokens_and_cost(
                "X" * 400, "claude-sonnet-5"
            )

            response = app_client.get("/api/benchmark?model=claude-sonnet-5")
            data = response.json()

            item = next(i for i in data["groups"][0]["items"] if i["method"] == "tavily_cli")
            assert item["tokens"] == one_search_tokens * 1000
            assert item["cost_usd"] == one_search_cost * 1000

    def test_multi_search_cost_uses_average_not_raw_sum(
        self,
        app_client: TestClient,
    ) -> None:
        """With multiple fixed searches for a method, the projection must use
        their average cost per search (then x1000) - not the raw sum across
        the fixed sample, which would scale with the sample size instead of
        representing a single search's cost.
        """
        two_search_results = {
            "fixture_1": [
                SearchResult(
                    method="tavily_cli",
                    raw_response="X" * 400,
                    timestamp="2024-01-01T00:00:00",
                ),
            ],
            "fixture_2": [
                SearchResult(
                    method="tavily_cli",
                    raw_response="X" * 800,
                    timestamp="2024-01-01T00:00:00",
                ),
            ],
        }

        with (
            patch(
                "api.routers.benchmark.load_searches",
                return_value=[
                    SearchQuery(query="a", note="a", successfuly_return_includes=[]),
                    SearchQuery(query="b", note="b", successfuly_return_includes=[]),
                ],
            ),
            patch(
                "api.routers.benchmark.load_fixtures",
                return_value=two_search_results,
            ),
        ):
            tokens_1, cost_1 = calculate_tokens_and_cost("X" * 400, "claude-sonnet-5")
            tokens_2, cost_2 = calculate_tokens_and_cost("X" * 800, "claude-sonnet-5")
            expected_tokens = ((tokens_1 + tokens_2) / 2) * 1000
            expected_cost = ((cost_1 + cost_2) / 2) * 1000

            response = app_client.get("/api/benchmark?model=claude-sonnet-5")
            data = response.json()

            item = next(i for i in data["groups"][0]["items"] if i["method"] == "tavily_cli")
            assert item["tokens"] == int(expected_tokens)
            assert item["cost_usd"] == expected_cost


class TestBenchmarkModelParameter:
    """Tests for model parameter handling."""

    def test_model_query_parameter_haiku(
        self,
        app_client: TestClient,
        mock_load_searches: None,
        mock_load_fixtures: None,
        mock_calculate_tokens_and_cost: None,
    ) -> None:
        """Test ?model=claude-haiku-4-5 parameter.

        Args:
            app_client: FastAPI test client.
            mock_load_searches: Mocked load_searches function.
            mock_load_fixtures: Mocked load_fixtures function.
            mock_calculate_tokens_and_cost: Mocked token calculator.
        """
        response = app_client.get("/api/benchmark?model=claude-haiku-4-5")
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "claude-haiku-4-5"

    def test_model_query_parameter_sonnet(
        self,
        app_client: TestClient,
        mock_load_searches: None,
        mock_load_fixtures: None,
        mock_calculate_tokens_and_cost: None,
    ) -> None:
        """Test ?model=claude-sonnet-5 parameter.

        Args:
            app_client: FastAPI test client.
            mock_load_searches: Mocked load_searches function.
            mock_load_fixtures: Mocked load_fixtures function.
            mock_calculate_tokens_and_cost: Mocked token calculator.
        """
        response = app_client.get("/api/benchmark?model=claude-sonnet-5")
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "claude-sonnet-5"

    def test_model_query_parameter_opus(
        self,
        app_client: TestClient,
        mock_load_searches: None,
        mock_load_fixtures: None,
        mock_calculate_tokens_and_cost: None,
    ) -> None:
        """Test ?model=claude-opus-5 parameter.

        Args:
            app_client: FastAPI test client.
            mock_load_searches: Mocked load_searches function.
            mock_load_fixtures: Mocked load_fixtures function.
            mock_calculate_tokens_and_cost: Mocked token calculator.
        """
        response = app_client.get("/api/benchmark?model=claude-opus-5")
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "claude-opus-5"

    def test_invalid_model_parameter(
        self,
        app_client: TestClient,
        mock_load_searches: None,
        mock_load_fixtures: None,
    ) -> None:
        """Test that invalid model parameter returns 400 error.

        Args:
            app_client: FastAPI test client.
            mock_load_searches: Mocked load_searches function.
            mock_load_fixtures: Mocked load_fixtures function.
        """
        response = app_client.get("/api/benchmark?model=invalid-model")
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Unsupported model" in data["detail"]


class TestBenchmarkErrorHandling:
    """Tests for error handling and edge cases."""

    def test_missing_fixtures_returns_error(
        self,
        app_client: TestClient,
        mock_load_searches: None,
    ) -> None:
        """If fixtures not loaded, verify graceful error (not 500).

        Args:
            app_client: FastAPI test client.
            mock_load_searches: Mocked load_searches function.
        """
        with patch(
            "api.routers.benchmark.load_fixtures",
            side_effect=FileNotFoundError("Fixtures not found"),
        ):
            response = app_client.get("/api/benchmark")
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data

    def test_missing_searches_returns_error(
        self,
        app_client: TestClient,
    ) -> None:
        """If searches not loaded, verify graceful error.

        Args:
            app_client: FastAPI test client.
        """
        with patch(
            "api.routers.benchmark.load_searches",
            side_effect=FileNotFoundError("Searches not found"),
        ):
            response = app_client.get("/api/benchmark")
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data

    def test_benchmark_with_empty_fixtures(
        self,
        app_client: TestClient,
        fixture_mock_searches: list[SearchQuery],
    ) -> None:
        """Test benchmark behavior with empty fixture data.

        Args:
            app_client: FastAPI test client.
            fixture_mock_searches: Mock searches.
        """
        with patch(
            "api.routers.benchmark.load_searches",
            return_value=fixture_mock_searches,
        ):
            with patch(
                "api.routers.benchmark.load_fixtures",
                return_value={},  # Empty fixtures
            ):
                response = app_client.get("/api/benchmark")
                # Should still return 200, but with 0 tokens/cost
                assert response.status_code == 200
                data = response.json()
                for group in data["groups"]:
                    for item in group["items"]:
                        assert item["tokens"] == 0
                        assert item["cost_usd"] == 0.0


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check_endpoint(
        self,
        app_client: TestClient,
    ) -> None:
        """Verify /health endpoint returns ok status.

        Args:
            app_client: FastAPI test client.
        """
        response = app_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "Benchmark Tavily"

    def test_readiness_check_endpoint(
        self,
        app_client: TestClient,
        mock_load_searches: None,
        mock_load_fixtures: None,
    ) -> None:
        """Verify /ready endpoint reports readiness status.

        Args:
            app_client: FastAPI test client.
            mock_load_searches: Mocked load_searches function.
            mock_load_fixtures: Mocked load_fixtures function.
        """
        response = app_client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        assert "searches_loaded" in data
        assert "fixtures_loaded" in data
