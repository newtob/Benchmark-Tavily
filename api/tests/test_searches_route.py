"""Tests for the searches listing endpoint."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from api.models.schemas import SearchQuery


class TestSearchesRoute:
    """Tests for GET /api/searches."""

    def test_get_searches_returns_200(
        self,
        app_client: TestClient,
        fixture_mock_searches: list[SearchQuery],
    ) -> None:
        """Verify that the /api/searches endpoint returns 200 OK."""
        with patch(
            "api.routers.searches.load_searches",
            return_value=fixture_mock_searches,
        ):
            response = app_client.get("/api/searches")
            assert response.status_code == 200

    def test_get_searches_returns_all_queries(
        self,
        app_client: TestClient,
        fixture_mock_searches: list[SearchQuery],
    ) -> None:
        """Verify that every search's query/note/successfuly_return_includes is returned."""
        with patch(
            "api.routers.searches.load_searches",
            return_value=fixture_mock_searches,
        ):
            response = app_client.get("/api/searches")
            data = response.json()

            assert len(data) == len(fixture_mock_searches)
            for expected, actual in zip(fixture_mock_searches, data, strict=True):
                assert actual["query"] == expected.query
                assert actual["note"] == expected.note
                assert actual["successfuly_return_includes"] == expected.successfuly_return_includes

    def test_missing_searches_returns_error(
        self,
        app_client: TestClient,
    ) -> None:
        """If searches.yaml can't be loaded, verify a graceful 500 (not an unhandled crash)."""
        with patch(
            "api.routers.searches.load_searches",
            side_effect=FileNotFoundError("Searches not found"),
        ):
            response = app_client.get("/api/searches")
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
