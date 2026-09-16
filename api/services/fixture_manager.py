"""Fixture manager for loading searches and cached results."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml

from api.models.schemas import SearchQuery, SearchResult

logger = logging.getLogger(__name__)

# Get the project root directory (parent of the api directory)
PROJECT_ROOT = Path(__file__).parent.parent.parent
SEARCHES_FILE = PROJECT_ROOT / "searches.yaml"
FIXTURES_DIR = PROJECT_ROOT / "api" / "fixtures"


def load_searches() -> list[SearchQuery]:
    """Load searches from searches.yaml.

    Returns:
        List of SearchQuery objects parsed from searches.yaml.

    Raises:
        FileNotFoundError: If searches.yaml is not found.
        ValueError: If searches.yaml is malformed or missing required fields.
    """
    if not SEARCHES_FILE.exists():
        raise FileNotFoundError(
            f"Searches file not found at {SEARCHES_FILE}. "
            "Please ensure searches.yaml exists in the project root."
        )

    try:
        with open(SEARCHES_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "searches" not in data:
            raise ValueError("searches.yaml must contain a 'searches' key")

        searches = []
        for item in data["searches"]:
            search = SearchQuery(
                query=item["query"],
                note=item["note"],
                successfuly_return_includes=item.get("successfuly_return_includes", []),
            )
            searches.append(search)

        logger.info(f"Loaded {len(searches)} searches from {SEARCHES_FILE}")
        return searches

    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse searches.yaml: {e}") from e


def load_fixtures() -> dict[str, list[SearchResult]]:
    """Load all fixture files from api/fixtures/ directory.

    Returns:
        Dictionary mapping fixture names to lists of SearchResult objects.
        If the fixtures directory doesn't exist, returns an empty dict.

    Raises:
        ValueError: If any fixture file is malformed.
    """
    fixtures: dict[str, list[SearchResult]] = {}

    if not FIXTURES_DIR.exists():
        logger.warning(
            f"Fixtures directory not found at {FIXTURES_DIR}. "
            "Running without cached fixtures (tests should mock/provide fixtures)."
        )
        return fixtures

    for fixture_file in sorted(FIXTURES_DIR.glob("*.json")):
        fixture_name = fixture_file.stem
        try:
            with open(fixture_file, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse fixture file {fixture_file}: {e}") from e

        items = data if isinstance(data, list) else [data]
        results = [
            SearchResult(
                method=item.get("method", "unknown"),
                raw_response=item.get("raw_response", ""),
                timestamp=item.get("timestamp", "2024-01-01T00:00:00"),
            )
            for item in items
        ]

        fixtures[fixture_name] = results
        logger.info(f"Loaded fixture {fixture_name} with {len(results)} results")

    logger.info(f"Loaded {len(fixtures)} fixture files from {FIXTURES_DIR}")
    return fixtures
