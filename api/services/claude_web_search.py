"""Table 2, "Claude Web Search" column.

Response data is produced by shelling out to the Claude Code CLI in
headless mode (`claude -p ... --output-format json`), authenticated via
the CLI's own OAuth/subscription login — never a raw ANTHROPIC_API_KEY,
which this org's policy disables issuing. See
specs/tavily-benchmark-app.md §4/§7/§14 for the full rationale.

`invoke_cli()` is called ONLY by scripts/record_benchmark_fixtures.py —
never by the running API service, live mode or not. The served app (and
fixture replay) only ever goes through `parse_cli_result()`, which is also
what `invoke_cli()` uses internally to shape its own output before writing
a fixture. This keeps the Claude Code CLI, its OAuth state, and Node/npm
entirely out of the runtime Docker image.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any

# `--bare` is deliberately NOT used: bare mode requires ANTHROPIC_API_KEY
# (which doesn't exist here) and skips MCP/hooks/CLAUDE.md loading. Without
# --bare, this subprocess loads this repo's own hooks/.mcp.json/CLAUDE.md —
# an accepted tradeoff, not an oversight (see §14's "ambient context
# leakage" note). CLAUDE_CODE_ENABLE_TELEMETRY/OTEL_* are explicitly unset
# below so these recording calls never land in the otel/ prompt-journal
# pipeline (specs/otel-collector-autostart.md §5's own boundary).
_ENV_VARS_TO_UNSET = (
    "CLAUDE_CODE_ENABLE_TELEMETRY",
    "OTEL_METRICS_EXPORTER",
    "OTEL_LOGS_EXPORTER",
    "OTEL_EXPORTER_OTLP_PROTOCOL",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_LOGS_EXPORT_INTERVAL",
)


@dataclass(frozen=True)
class ClaudeWebSearchRecording:
    question: str
    response_text: str  # the CLI JSON's `result` field — tokenized identically
    #                     to tavily_extract's content by tokenizer.py
    latency_ms: float  # wall-clock subprocess time — NOT apples-to-apples with
    #                    tavily_extract's raw-HTTP latency (see §6)
    response_bytes: int  # len(response_text.encode()) — payload-text bytes
    session_id: str  # provenance/debugging only; never read by pricing.py
    model: str  # the --model value actually used
    total_cost_usd: float | None  # provenance/debugging only; never read by pricing.py


async def invoke_cli(
    question: str, *, model: str = "sonnet", timeout_s: float = 120
) -> ClaudeWebSearchRecording:
    """Run `claude -p` in headless mode for one question. Live-mode only,
    called only by the recording script. Requires the Claude Code CLI
    installed and authenticated (`claude /login`) on this machine.

    Flags below are believed correct as of this writing but are flagged for
    verification against the installed CLI version at implementation time
    (see specs/tavily-benchmark-app.md §14): `--permission-prompts none`
    needs Claude Code v2.1.259+ (fall back to `--permission-mode dontAsk`
    on older versions).
    """
    import os

    env = {k: v for k, v in os.environ.items() if k not in _ENV_VARS_TO_UNSET}

    args = [
        "claude",
        "-p",
        question,
        "--output-format",
        "json",
        "--allowedTools",
        "WebSearch",
        "--permission-mode",
        "default",
        "--permission-prompts",
        "none",
        "--model",
        model,
    ]

    started = time.monotonic()
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except TimeoutError:
        proc.kill()
        msg = f"claude -p timed out after {timeout_s}s for question: {question!r}"
        raise RuntimeError(msg) from None
    latency_ms = (time.monotonic() - started) * 1000

    if proc.returncode != 0:
        raise RuntimeError(
            f"claude -p exited {proc.returncode} for question {question!r}: "
            f"{stderr.decode(errors='replace')}"
        )

    raw_json = json.loads(stdout.decode())
    return parse_cli_result(question, raw_json, latency_ms=latency_ms)


def parse_cli_result(
    question: str, raw_json: dict[str, Any], *, latency_ms: float = 0.0
) -> ClaudeWebSearchRecording:
    response_text = raw_json.get("result", "")
    return ClaudeWebSearchRecording(
        question=question,
        response_text=response_text,
        latency_ms=latency_ms,
        response_bytes=len(response_text.encode()),
        session_id=raw_json.get("session_id", ""),
        model=raw_json.get("model", ""),
        total_cost_usd=raw_json.get("total_cost_usd"),
    )
