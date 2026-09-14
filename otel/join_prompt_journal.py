#!/usr/bin/env python3
"""
Join otel/output/prompt_costs.json (per-prompt token/cost, keyed by
prompt_id — produced by parse_prompt_costs.py) against
otel/output/prompt_journal.jsonl (prompt text/summary, keyed by the same
prompt_id — appended live by scripts/hooks/log-prompt.sh) so you can see
what a prompt actually was next to what it cost.

The join key is an exact prompt_id match, not chronological-order
guessing: Claude Code hooks receive a `prompt_id` field that is the same
UUID as the `prompt.id` attribute OTel's telemetry uses for the same turn.

Usage:
    python3 otel/join_prompt_journal.py

Writes otel/output/prompt_report.json and prints a summary table to stdout.
Run `just otel-parse` first so prompt_costs.json is up to date.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
COSTS_PATH = HERE / "output" / "prompt_costs.json"
JOURNAL_PATH = HERE / "output" / "prompt_journal.jsonl"
REPORT_PATH = HERE / "output" / "prompt_report.json"

SUMMARY_MAX_CHARS = 120


def load_costs(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path) as f:
        data: list[dict[str, Any]] = json.load(f)
        return data


def load_journal(path: Path) -> dict[str, dict[str, Any]]:
    """Return the *last* journal entry seen per prompt_id (a prompt could in
    principle be logged more than once; the most recent entry wins)."""
    entries: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return entries
    with open(path) as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                print(f"warning: skipping malformed JSON on line {line_no}", file=sys.stderr)
                continue
            prompt_id = row.get("prompt_id")
            if isinstance(prompt_id, str):
                entries[prompt_id] = row
    return entries


def summarize(text: str | None) -> str | None:
    if not text:
        return None
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    if len(first_line) > SUMMARY_MAX_CHARS:
        return first_line[:SUMMARY_MAX_CHARS].rstrip() + "…"
    return first_line or None


def main() -> None:
    costs = load_costs(COSTS_PATH)
    journal = load_journal(JOURNAL_PATH)

    seen_prompt_ids = {row["prompt_id"] for row in costs if isinstance(row.get("prompt_id"), str)}

    report = []
    for row in costs:
        prompt_id = row.get("prompt_id")
        journal_entry = journal.get(prompt_id) if isinstance(prompt_id, str) else None
        prompt_text = journal_entry.get("prompt_text") if journal_entry else None
        report.append(
            {
                "prompt_index": row.get("prompt_index"),
                "prompt_id": prompt_id,
                "cost_usd": row.get("cost_usd"),
                "input_tokens": row.get("input_tokens"),
                "output_tokens": row.get("output_tokens"),
                "num_api_requests": row.get("num_api_requests"),
                "summary": summarize(prompt_text),
                "has_journal_entry": journal_entry is not None,
            }
        )

    # Journal entries with no matching cost row: a submitted prompt that
    # never produced a claude_code.api_request event (e.g. hook-blocked).
    # Surface them with null cost rather than silently dropping them.
    for prompt_id, journal_entry in journal.items():
        if prompt_id in seen_prompt_ids:
            continue
        report.append(
            {
                "prompt_index": None,
                "prompt_id": prompt_id,
                "cost_usd": None,
                "input_tokens": None,
                "output_tokens": None,
                "num_api_requests": 0,
                "summary": summarize(journal_entry.get("prompt_text")),
                "has_journal_entry": True,
            }
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)

    if not report:
        print("No prompt cost or journal data found yet.")
        print(f"(expected {COSTS_PATH} and/or {JOURNAL_PATH})")
        return

    header = f"{'#':>3}  {'cost_usd':>10}  {'in_tok':>8}  {'out_tok':>8}  {'calls':>5}  summary"
    print(header)
    for r in report:
        idx = r["prompt_index"] if r["prompt_index"] is not None else "?"
        cost = f"{r['cost_usd']:.6f}" if r["cost_usd"] is not None else "(no cost)"
        in_tok = r["input_tokens"] if r["input_tokens"] is not None else "-"
        out_tok = r["output_tokens"] if r["output_tokens"] is not None else "-"
        summary = r["summary"] or "(no journal entry)"
        calls = r["num_api_requests"]
        print(f"{idx!s:>3}  {cost:>10}  {in_tok!s:>8}  {out_tok!s:>8}  {calls:>5}  {summary}")

    print(f"\n{len(report)} prompts. Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
