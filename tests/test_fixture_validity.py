"""Guards against the benchmark silently reporting made-up or mis-measured data.
See specs/tavily-benchmark-app.md §6."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from api.services.claude_web_search import parse_stream_events

FIXTURES = Path(__file__).resolve().parent.parent / "api" / "fixtures"
FIXTURE_FILES = sorted((FIXTURES / "web_content").glob("*/*.json"))
CLAUDE_FILES = sorted((FIXTURES / "web_content" / "claude_web_search").glob("*.json"))


def test_fixtures_exist() -> None:
    assert len(FIXTURE_FILES) == 30


@pytest.mark.parametrize("path", FIXTURE_FILES, ids=lambda p: str(p.relative_to(FIXTURES)))
def test_no_placeholder_fixtures(path: Path) -> None:
    data = json.loads(path.read_text())
    assert "_placeholder_note" not in data, (
        f"{path.relative_to(FIXTURES)} is a hand-authored placeholder; "
        "run `just record-fixtures` to replace it with real recorded data"
    )


# Claude Code's WebFetch refuses some hosts (e.g. www.bbc.co.uk): the recorded
# fixture is the model's "unable to fetch" turn, with an empty tool result.
KNOWN_BLOCKED = {"3.json"}
CLAUDE_PARAMS = [
    pytest.param(
        p,
        id=p.name,
        marks=pytest.mark.xfail(reason="Claude Code WebFetch blocks this host")
        if p.name in KNOWN_BLOCKED
        else (),
    )
    for p in CLAUDE_FILES
]


@pytest.mark.parametrize("path", CLAUDE_PARAMS)
def test_claude_fixtures_measure_real_search_ingestion(path: Path) -> None:
    data = json.loads(path.read_text())
    assert data["web_search_calls"] >= 1
    assert data["search_ingest_tokens"] > 0
    assert data["tool_result_text"]
    assert not data["session_id"].startswith("placeholder")


def _assistant(msg_id: str, inp: int, out: int, block: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "assistant",
        "message": {
            "id": msg_id,
            "content": [block],
            "usage": {
                "input_tokens": 2,
                "cache_creation_input_tokens": inp - 2,
                "cache_read_input_tokens": 0,
                "output_tokens": out,
            },
        },
    }


def test_parse_stream_events_ingest_is_usage_delta() -> None:
    events: list[dict[str, Any]] = [
        _assistant("m1", 3635, 24, {"type": "tool_use", "name": "WebFetch"}),
        {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "content": "links and text"}]},
        },
        _assistant("m2", 5494, 667, {"type": "text", "text": "answer"}),
        {"type": "result", "result": "answer", "session_id": "s", "usage": {}, "modelUsage": {}},
    ]
    rec = parse_stream_events("q", events)
    assert rec.search_ingest_tokens == 5494 - 3635 - 24
    assert rec.web_search_calls == 1
    assert rec.tool_result_text == "links and text"


def test_parse_stream_events_without_search_ingests_nothing() -> None:
    events: list[dict[str, Any]] = [
        _assistant("m1", 2000, 5, {"type": "text", "text": "from memory"}),
        {"type": "result", "result": "from memory"},
    ]
    rec = parse_stream_events("q", events)
    assert rec.web_search_calls == 0
    assert rec.search_ingest_tokens == 0
