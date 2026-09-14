"""Loads the hand-curated benchmark-scenario YAML files (see
specs/tavily-benchmark-app.md §4) — the fixed query set for Table 1 and the
fixed URL+question set for Table 2. Used by both the recording script and,
indirectly, by fixtures.py (which keys recorded response fixtures by the
same query/URL text these files define).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent.parent  # api/
TOOL_CALL_INPUTS_PATH = HERE / "fixtures" / "tool_call" / "inputs.yaml"
WEB_CONTENT_INPUTS_PATH = HERE / "fixtures" / "web_content" / "inputs.yaml"


@dataclass(frozen=True)
class ToolCallQuery:
    query: str
    note: str = ""


@dataclass(frozen=True)
class WebContentPair:
    url: str
    question: str
    note: str = ""


def load_tool_call_queries(path: Path = TOOL_CALL_INPUTS_PATH) -> list[ToolCallQuery]:
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return [
        ToolCallQuery(query=item["query"], note=item.get("note", ""))
        for item in data.get("tool_call_queries", [])
    ]


def load_web_content_pairs(path: Path = WEB_CONTENT_INPUTS_PATH) -> list[WebContentPair]:
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return [
        WebContentPair(url=item["url"], question=item["question"], note=item.get("note", ""))
        for item in data.get("web_content_pairs", [])
    ]
