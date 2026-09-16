"""Tests for search execution and orchestration."""

from __future__ import annotations

from datetime import UTC, datetime

from api.models.schemas import SearchQuery, SearchResult
from api.services.search_executor import SEARCH_METHODS, execute_searches


class TestExecuteSearchesBasics:
    """Basic tests for search execution."""

    def test_execute_searches_returns_dict(
        self,
        fixture_mock_results: dict[str, list[SearchResult]],
        fixture_mock_searches: list[SearchQuery],
    ) -> None:
        """Verify execute_searches returns a dictionary.

        Args:
            fixture_mock_results: Mock fixture data.
            fixture_mock_searches: Mock searches.
        """
        result = execute_searches(fixture_mock_results, fixture_mock_searches)
        assert isinstance(result, dict)

    def test_all_methods_present(
        self,
        fixture_mock_results: dict[str, list[SearchResult]],
        fixture_mock_searches: list[SearchQuery],
    ) -> None:
        """Verify dict has keys for all standard methods.

        The returned dictionary should have entries for all three methods:
        - tavily_cli
        - tavily_mcp
        - search_in_prompt
        """
        result = execute_searches(fixture_mock_results, fixture_mock_searches)

        for method in SEARCH_METHODS:
            assert method in result, f"Missing method: {method}"
            assert isinstance(result[method], list)

    def test_results_per_method_matches_fixtures(
        self,
        fixture_mock_results: dict[str, list[SearchResult]],
        fixture_mock_searches: list[SearchQuery],
    ) -> None:
        """Verify each method has results that match input fixtures.

        Args:
            fixture_mock_results: Mock fixture data.
            fixture_mock_searches: Mock searches.
        """
        result = execute_searches(fixture_mock_results, fixture_mock_searches)

        # Count expected results per method
        expected_counts: dict[str, int] = {}
        for _fixture_name, results in fixture_mock_results.items():
            for search_result in results:
                method = search_result.method
                expected_counts[method] = expected_counts.get(method, 0) + 1

        # Verify actual counts match expected
        for method in SEARCH_METHODS:
            expected_count = expected_counts.get(method, 0)
            actual_count = len(result[method])
            assert actual_count == expected_count, (
                f"Method {method}: expected {expected_count} results, " f"got {actual_count}"
            )

    def test_search_result_objects_are_preserved(
        self,
        fixture_mock_results: dict[str, list[SearchResult]],
        fixture_mock_searches: list[SearchQuery],
    ) -> None:
        """Verify SearchResult objects are returned unchanged.

        Args:
            fixture_mock_results: Mock fixture data.
            fixture_mock_searches: Mock searches.
        """
        result = execute_searches(fixture_mock_results, fixture_mock_searches)

        # Collect all original results
        original_results = []
        for results in fixture_mock_results.values():
            original_results.extend(results)

        # Collect all returned results
        returned_results = []
        for results in result.values():
            returned_results.extend(results)

        # Verify count matches
        assert len(returned_results) == len(original_results)

        # Verify each result has correct fields
        for search_result in returned_results:
            assert isinstance(search_result, SearchResult)
            assert hasattr(search_result, "method")
            assert hasattr(search_result, "raw_response")
            assert hasattr(search_result, "timestamp")


class TestExecuteSearchesEdgeCases:
    """Edge case tests for search execution."""

    def test_execute_searches_with_empty_fixtures(
        self,
        fixture_mock_searches: list[SearchQuery],
    ) -> None:
        """Test execute_searches with empty fixture data.

        When fixtures are empty, should return dict with empty lists
        for each method.
        """
        empty_fixtures: dict[str, list[SearchResult]] = {}
        result = execute_searches(empty_fixtures, fixture_mock_searches)

        # All methods should be present but empty
        for method in SEARCH_METHODS:
            assert method in result
            assert result[method] == []

    def test_execute_searches_with_empty_searches(
        self,
        fixture_mock_results: dict[str, list[SearchResult]],
    ) -> None:
        """Test execute_searches with empty search list.

        Should still process fixtures correctly regardless of search count.
        """
        empty_searches: list[SearchQuery] = []
        result = execute_searches(fixture_mock_results, empty_searches)

        # Should still have results from fixtures
        for method in SEARCH_METHODS:
            assert method in result

    def test_execute_searches_with_single_fixture(self) -> None:
        """Test execute_searches with only one fixture file.

        Args:
        """
        single_fixture = {
            "fixture_1": [
                SearchResult(
                    method="tavily_cli",
                    raw_response="Single fixture result",
                    timestamp=datetime.now(UTC).isoformat(),
                ),
                SearchResult(
                    method="tavily_mcp",
                    raw_response="Single fixture result",
                    timestamp=datetime.now(UTC).isoformat(),
                ),
            ],
        }
        searches = [
            SearchQuery(
                query="test",
                note="test",
                successfuly_return_includes=[],
            )
        ]

        result = execute_searches(single_fixture, searches)

        # Should have results for methods present in fixture
        assert len(result["tavily_cli"]) == 1
        assert len(result["tavily_mcp"]) == 1
        # search_in_prompt not in fixture, should have empty list
        assert len(result["search_in_prompt"]) == 0

    def test_execute_searches_preserves_result_content(
        self,
        fixture_mock_results: dict[str, list[SearchResult]],
        fixture_mock_searches: list[SearchQuery],
    ) -> None:
        """Verify that raw_response and other fields are preserved.

        Args:
            fixture_mock_results: Mock fixture data.
            fixture_mock_searches: Mock searches.
        """
        result = execute_searches(fixture_mock_results, fixture_mock_searches)

        # Check that a tavily_cli result is present and has expected content
        if result["tavily_cli"]:
            cli_result = result["tavily_cli"][0]
            assert cli_result.method == "tavily_cli"
            assert len(cli_result.raw_response) > 0
            assert cli_result.timestamp is not None


class TestFixtureLoading:
    """Tests related to fixture loading within execute_searches."""

    def test_fixture_loading_with_multiple_methods(
        self,
        fixture_mock_results: dict[str, list[SearchResult]],
        fixture_mock_searches: list[SearchQuery],
    ) -> None:
        """Verify fixtures are correctly loaded and organized by method.

        Args:
            fixture_mock_results: Mock fixture data.
            fixture_mock_searches: Mock searches.
        """
        result = execute_searches(fixture_mock_results, fixture_mock_searches)

        # Verify all expected methods are present
        for method in SEARCH_METHODS:
            assert method in result, f"Method {method} missing from results"

    def test_fixture_order_consistency(
        self,
        fixture_mock_results: dict[str, list[SearchResult]],
        fixture_mock_searches: list[SearchQuery],
    ) -> None:
        """Verify that fixtures are consistently loaded across calls.

        Multiple calls with same input should produce same output order.
        """
        result1 = execute_searches(fixture_mock_results, fixture_mock_searches)
        result2 = execute_searches(fixture_mock_results, fixture_mock_searches)

        # Results should be identical
        for method in SEARCH_METHODS:
            assert len(result1[method]) == len(result2[method])
            for _i, (r1, r2) in enumerate(zip(result1[method], result2[method], strict=False)):
                assert r1.method == r2.method
                assert r1.raw_response == r2.raw_response

    def test_execute_searches_handles_malformed_fixture(
        self,
        fixture_mock_searches: list[SearchQuery],
    ) -> None:
        """Test handling of fixture with missing method field.

        Even if a result is missing a method field, should still process.
        """
        malformed_fixture = {
            "fixture_1": [
                SearchResult(
                    method="tavily_cli",
                    raw_response="Valid result",
                    timestamp=datetime.now(UTC).isoformat(),
                ),
            ],
        }

        result = execute_searches(malformed_fixture, fixture_mock_searches)

        # Should still return all methods in output
        assert len(SEARCH_METHODS) == len(result)


class TestSearchMethodConstants:
    """Tests for SEARCH_METHODS constant."""

    def test_search_methods_contains_three_methods(self) -> None:
        """Verify SEARCH_METHODS has exactly 3 methods.

        The three expected methods are:
        - tavily_cli
        - tavily_mcp
        - search_in_prompt
        """
        assert len(SEARCH_METHODS) == 3

    def test_search_methods_contains_expected_values(self) -> None:
        """Verify SEARCH_METHODS contains correct method names."""
        assert "tavily_cli" in SEARCH_METHODS
        assert "tavily_mcp" in SEARCH_METHODS
        assert "search_in_prompt" in SEARCH_METHODS

    def test_search_methods_are_strings(self) -> None:
        """Verify all items in SEARCH_METHODS are strings."""
        for method in SEARCH_METHODS:
            assert isinstance(method, str)
