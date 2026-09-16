"""Tests for the fixture manager (loading searches.yaml and api/fixtures/*.json)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from api.services import fixture_manager


class TestLoadSearches:
    """Tests for load_searches()."""

    def test_load_searches_returns_parsed_queries(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A well-formed searches.yaml is parsed into SearchQuery objects."""
        searches_file = tmp_path / "searches.yaml"
        searches_file.write_text(
            yaml.dump(
                {
                    "searches": [
                        {
                            "query": "test query",
                            "note": "test note",
                            "successfuly_return_includes": ["a", "b"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(fixture_manager, "SEARCHES_FILE", searches_file)

        result = fixture_manager.load_searches()

        assert len(result) == 1
        assert result[0].query == "test query"
        assert result[0].note == "test note"
        assert result[0].successfuly_return_includes == ["a", "b"]

    def test_load_searches_missing_file_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A missing searches.yaml raises FileNotFoundError."""
        monkeypatch.setattr(fixture_manager, "SEARCHES_FILE", tmp_path / "does_not_exist.yaml")

        with pytest.raises(FileNotFoundError):
            fixture_manager.load_searches()

    def test_load_searches_missing_searches_key_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A YAML file without a 'searches' key raises ValueError."""
        searches_file = tmp_path / "searches.yaml"
        searches_file.write_text(yaml.dump({"other_key": []}), encoding="utf-8")
        monkeypatch.setattr(fixture_manager, "SEARCHES_FILE", searches_file)

        with pytest.raises(ValueError, match="searches"):
            fixture_manager.load_searches()

    def test_load_searches_invalid_yaml_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Malformed YAML raises ValueError, not a raw YAMLError."""
        searches_file = tmp_path / "searches.yaml"
        searches_file.write_text("searches: [\n  - unterminated", encoding="utf-8")
        monkeypatch.setattr(fixture_manager, "SEARCHES_FILE", searches_file)

        with pytest.raises(ValueError, match="Failed to parse"):
            fixture_manager.load_searches()

    def test_load_searches_defaults_missing_includes_field(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A search item without successfuly_return_includes defaults to []."""
        searches_file = tmp_path / "searches.yaml"
        searches_file.write_text(
            yaml.dump({"searches": [{"query": "q", "note": "n"}]}),
            encoding="utf-8",
        )
        monkeypatch.setattr(fixture_manager, "SEARCHES_FILE", searches_file)

        result = fixture_manager.load_searches()

        assert result[0].successfuly_return_includes == []


class TestLoadFixtures:
    """Tests for load_fixtures()."""

    def test_load_fixtures_missing_dir_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A missing fixtures directory returns an empty dict, not an error."""
        monkeypatch.setattr(fixture_manager, "FIXTURES_DIR", tmp_path / "no_such_dir")

        result = fixture_manager.load_fixtures()

        assert result == {}

    def test_load_fixtures_parses_list_shaped_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A fixture file containing a JSON list of results is parsed correctly."""
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        (fixtures_dir / "searches_tavily_cli_0.json").write_text(
            json.dumps(
                [
                    {"method": "tavily_cli", "raw_response": "hello", "timestamp": "t"},
                    {"method": "tavily_cli", "raw_response": "world", "timestamp": "t"},
                ]
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(fixture_manager, "FIXTURES_DIR", fixtures_dir)

        result = fixture_manager.load_fixtures()

        assert list(result.keys()) == ["searches_tavily_cli_0"]
        assert len(result["searches_tavily_cli_0"]) == 2
        assert result["searches_tavily_cli_0"][0].raw_response == "hello"

    def test_load_fixtures_parses_single_object_shaped_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A fixture file containing a single JSON object is wrapped in a list."""
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        (fixtures_dir / "single.json").write_text(
            json.dumps({"method": "tavily_mcp", "raw_response": "x", "timestamp": "t"}),
            encoding="utf-8",
        )
        monkeypatch.setattr(fixture_manager, "FIXTURES_DIR", fixtures_dir)

        result = fixture_manager.load_fixtures()

        assert len(result["single"]) == 1
        assert result["single"][0].method == "tavily_mcp"

    def test_load_fixtures_multiple_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Multiple fixture files are all loaded, keyed by filename stem."""
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        for name in ("a", "b", "c"):
            (fixtures_dir / f"{name}.json").write_text(
                json.dumps([{"method": "tavily_cli", "raw_response": name, "timestamp": "t"}]),
                encoding="utf-8",
            )
        monkeypatch.setattr(fixture_manager, "FIXTURES_DIR", fixtures_dir)

        result = fixture_manager.load_fixtures()

        assert set(result.keys()) == {"a", "b", "c"}

    def test_load_fixtures_malformed_json_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Malformed JSON in a fixture file raises ValueError."""
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        (fixtures_dir / "broken.json").write_text("{not valid json", encoding="utf-8")
        monkeypatch.setattr(fixture_manager, "FIXTURES_DIR", fixtures_dir)

        with pytest.raises(ValueError, match="Failed to parse"):
            fixture_manager.load_fixtures()

    def test_load_fixtures_missing_fields_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing method/raw_response/timestamp fields fall back to defaults."""
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        (fixtures_dir / "partial.json").write_text(json.dumps([{}]), encoding="utf-8")
        monkeypatch.setattr(fixture_manager, "FIXTURES_DIR", fixtures_dir)

        result = fixture_manager.load_fixtures()

        assert result["partial"][0].method == "unknown"
        assert result["partial"][0].raw_response == ""
