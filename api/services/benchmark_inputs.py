"""Loads the hand-curated page-load scenarios (see
specs/tavily-benchmark-app.md §4/§17) — the fixed URL set every method loads.
Used by both the recording script and, indirectly, by fixtures.py (which keys
recorded response fixtures positionally by this file's order).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent.parent  # api/
WEB_CONTENT_INPUTS_PATH = HERE / "fixtures" / "web_content" / "inputs.yaml"


@dataclass(frozen=True)
class WebContentPage:
    url: str
    note: str = ""


def load_web_content_pages(path: Path = WEB_CONTENT_INPUTS_PATH) -> list[WebContentPage]:
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return [
        WebContentPage(url=item["url"], note=item.get("note", ""))
        for item in data.get("web_content_pages", [])
    ]
