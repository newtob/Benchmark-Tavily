#!/usr/bin/env python3
"""
Parse the OTel Collector's file-exported logs (OTLP JSON, one ExportLogsServiceRequest
per line) and aggregate Claude Code's `claude_code.api_request` events by `prompt.id`
to reconstruct per-prompt token usage and cost.

Usage:
    python3 otel/parse_prompt_costs.py [path/to/otel-logs.jsonl]

Writes otel/output/prompt_costs.json and prints a summary table to stdout.
"""

from __future__ import annotations

import datetime
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = HERE / "output" / "otel-logs.jsonl"
DEFAULT_OUTPUT = HERE / "output" / "prompt_costs.json"

AttrValue = str | int | float | bool | None


def attr_value(value: dict[str, Any]) -> AttrValue:
    """Extract a Python value from an OTLP AnyValue JSON object."""
    if "stringValue" in value:
        return str(value["stringValue"])
    if "intValue" in value:
        return int(value["intValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "boolValue" in value:
        return bool(value["boolValue"])
    return None


def flatten_attrs(attr_list: list[dict[str, Any]] | None) -> dict[str, AttrValue]:
    out: dict[str, AttrValue] = {}
    for attr in attr_list or []:
        key = attr.get("key")
        if not isinstance(key, str):
            continue
        out[key] = attr_value(attr.get("value", {}))
    return out


def iter_log_records(path: Path) -> Iterator[dict[str, Any]]:
    with open(path) as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                batch = json.loads(line)
            except json.JSONDecodeError:
                print(f"warning: skipping malformed JSON on line {line_no}", file=sys.stderr)
                continue
            for resource_logs in batch.get("resourceLogs", []):
                for scope_logs in resource_logs.get("scopeLogs", []):
                    yield from scope_logs.get("logRecords", [])


def main() -> None:
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    if not input_path.exists():
        print(
            f"error: {input_path} not found — is the collector running "
            "and has Claude Code sent any requests?",
            file=sys.stderr,
        )
        sys.exit(1)

    prompts: dict[str, dict[str, Any]] = {}  # prompt_id -> aggregate dict
    order: list[str] = []  # prompt_id in first-seen order

    for record in iter_log_records(input_path):
        attrs = flatten_attrs(record.get("attributes"))
        if attrs.get("event.name") != "api_request":
            continue

        prompt_id_raw = attrs.get("prompt.id")
        prompt_id = prompt_id_raw if isinstance(prompt_id_raw, str) else "(unknown)"
        time_unix_nano = int(record.get("timeUnixNano", 0) or 0)

        if prompt_id not in prompts:
            prompts[prompt_id] = {
                "prompt_id": prompt_id,
                "first_seen_unix_nano": time_unix_nano,
                "num_api_requests": 0,
                "models": set(),
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_tokens": 0,
                "cache_creation_tokens": 0,
                "cost_usd": 0.0,
            }
            order.append(prompt_id)

        agg = prompts[prompt_id]
        agg["first_seen_unix_nano"] = (
            min(agg["first_seen_unix_nano"], time_unix_nano)
            if agg["first_seen_unix_nano"]
            else time_unix_nano
        )
        agg["num_api_requests"] += 1
        if attrs.get("model"):
            agg["models"].add(attrs["model"])
        agg["input_tokens"] += attrs.get("input_tokens", 0) or 0
        agg["output_tokens"] += attrs.get("output_tokens", 0) or 0
        agg["cache_read_tokens"] += attrs.get("cache_read_tokens", 0) or 0
        agg["cache_creation_tokens"] += attrs.get("cache_creation_tokens", 0) or 0
        agg["cost_usd"] += attrs.get("cost_usd", 0.0) or 0.0

    order.sort(key=lambda pid: prompts[pid]["first_seen_unix_nano"])

    results = []
    for idx, prompt_id in enumerate(order, 1):
        agg = prompts[prompt_id]
        ns = agg["first_seen_unix_nano"]
        first_seen_iso = None
        if ns:
            first_seen_iso = datetime.datetime.fromtimestamp(ns / 1e9, tz=datetime.UTC).isoformat()
        results.append(
            {
                "prompt_index": idx,
                "prompt_id": prompt_id,
                "first_seen": first_seen_iso,
                "num_api_requests": agg["num_api_requests"],
                "models": sorted(agg["models"]),
                "input_tokens": agg["input_tokens"],
                "output_tokens": agg["output_tokens"],
                "cache_read_tokens": agg["cache_read_tokens"],
                "cache_creation_tokens": agg["cache_creation_tokens"],
                "cost_usd": round(agg["cost_usd"], 6),
            }
        )

    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(DEFAULT_OUTPUT, "w") as f:
        json.dump(results, f, indent=2)

    if not results:
        print("No claude_code.api_request events found yet.")
        return

    header = (
        f"{'#':>3}  {'input':>8}  {'output':>8}  {'cache_r':>8}  "
        f"{'cache_c':>8}  {'cost_usd':>10}  {'calls':>5}  models"
    )
    print(header)
    total_cost = 0.0
    for r in results:
        total_cost += r["cost_usd"]
        print(
            f"{r['prompt_index']:>3}  {r['input_tokens']:>8}  {r['output_tokens']:>8}  "
            f"{r['cache_read_tokens']:>8}  {r['cache_creation_tokens']:>8}  "
            f"{r['cost_usd']:>10.6f}  {r['num_api_requests']:>5}  {', '.join(r['models'])}"
        )
    print(f"\n{len(results)} prompts, total cost: ${total_cost:.6f}")
    print(f"Wrote {DEFAULT_OUTPUT}")


if __name__ == "__main__":
    main()
