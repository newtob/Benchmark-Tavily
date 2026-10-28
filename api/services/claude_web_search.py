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
import os
import tempfile
import time
from dataclasses import dataclass, field
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


# Page-load leg: Claude loads the URL with its built-in WebFetch tool (the
# counterpart of Tavily Extract / TinyFish Fetch). Field names below still say
# "web_search" for fixture compatibility; they count calls to this tool.
_TOOL = "WebFetch"


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
    # Measured (not estimated) ingestion of the WebSearch tool_result by the
    # model: for each API call that issued WebSearch, the next call's total
    # input tokens (input + cache_creation + cache_read) minus that call's
    # own total input and output tokens. Sums every search round. This is
    # what fixtures.py reports as the Claude cell's `tokens`.
    search_ingest_tokens: int = 0
    web_search_calls: int = 0  # number of WebSearch tool_use blocks observed
    tool_result_text: str = ""  # the text the model actually ingested
    api_calls: list[dict[str, int]] = field(default_factory=list)  # per-call usage
    usage: dict[str, Any] = field(default_factory=dict)  # CLI result's whole-turn usage


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
    env = {k: v for k, v in os.environ.items() if k not in _ENV_VARS_TO_UNSET}

    # Isolation: a clean empty cwd (no CLAUDE.md/.mcp.json/hooks from this
    # repo), only the WebSearch built-in, no MCP servers, no skills. Without
    # this the model answers via ToolSearch/Context7 and never searches, and
    # carries ~30k tokens of ambient context. `--append-system-prompt` forces
    # a search so the recording actually exercises the tool.
    cwd = tempfile.mkdtemp(prefix="claude-ws-")
    mcp_config = os.path.join(cwd, "empty-mcp.json")
    with open(mcp_config, "w") as f:
        f.write('{"mcpServers":{}}')

    args = [
        "claude",
        "-p",
        question,
        "--append-system-prompt",
        "You must call the WebFetch tool at least once before answering; "
        "do not answer from memory.",
        "--output-format",
        "stream-json",
        "--verbose",
        "--tools",
        _TOOL,
        "--allowedTools",
        _TOOL,
        "--strict-mcp-config",
        "--mcp-config",
        mcp_config,
        "--setting-sources",
        "project",
        "--disable-slash-commands",
        "--permission-mode",
        "default",
        "--permission-prompts",
        "none",
        "--no-session-persistence",
        "--model",
        model,
    ]

    started = time.monotonic()
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd=cwd,
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

    events = [json.loads(line) for line in stdout.decode().splitlines() if line.strip()]
    recording = parse_stream_events(question, events, latency_ms=latency_ms)
    if recording.web_search_calls == 0 or recording.search_ingest_tokens <= 0:
        msg = (
            f"no measurable WebSearch ingestion for {question!r} "
            f"(search calls={recording.web_search_calls}, "
            f"ingest={recording.search_ingest_tokens}) — search was denied or skipped"
        )
        raise RuntimeError(msg)
    return recording


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


def _total_input(usage: dict[str, Any]) -> int:
    return (
        int(usage.get("input_tokens", 0))
        + int(usage.get("cache_creation_input_tokens", 0))
        + int(usage.get("cache_read_input_tokens", 0))
    )


def parse_stream_events(
    question: str, events: list[dict[str, Any]], *, latency_ms: float = 0.0
) -> ClaudeWebSearchRecording:
    """Build a recording from `claude -p --output-format stream-json --verbose`
    events, measuring how many tokens the model ingested from WebSearch."""
    calls: list[dict[str, int]] = []  # one per distinct API message id
    issued_search: list[bool] = []
    index_by_id: dict[str, int] = {}
    tool_results: list[str] = []
    result_event: dict[str, Any] = {}

    for event in events:
        kind = event.get("type")
        if kind == "assistant":
            message = event["message"]
            msg_id = message.get("id", "")
            usage = message.get("usage", {})
            if msg_id not in index_by_id:
                index_by_id[msg_id] = len(calls)
                calls.append({})
                issued_search.append(False)
            i = index_by_id[msg_id]
            calls[i] = {
                "input_total": _total_input(usage),
                "output_tokens": int(usage.get("output_tokens", 0)),
            }
            for block in message.get("content", []):
                if block.get("type") == "tool_use" and block.get("name") == _TOOL:
                    issued_search[i] = True
        elif kind == "user":
            content = event.get("message", {}).get("content", [])
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "tool_result" and not block.get("is_error"):
                        body = block.get("content", "")
                        tool_results.append(body if isinstance(body, str) else json.dumps(body))
        elif kind == "result":
            result_event = event

    ingest = 0
    searches = 0
    for i, did_search in enumerate(issued_search):
        if not did_search:
            continue
        searches += 1
        if i + 1 < len(calls):
            ingest += (
                calls[i + 1]["input_total"] - calls[i]["input_total"] - calls[i]["output_tokens"]
            )

    response_text = result_event.get("result", "")
    return ClaudeWebSearchRecording(
        question=question,
        response_text=response_text,
        latency_ms=latency_ms,
        response_bytes=len(response_text.encode()),
        session_id=result_event.get("session_id", ""),
        model=next(iter(result_event.get("modelUsage", {})), ""),
        total_cost_usd=result_event.get("total_cost_usd"),
        search_ingest_tokens=max(ingest, 0),
        web_search_calls=searches,
        tool_result_text="\n\n".join(tool_results),
        api_calls=calls,
        usage=result_event.get("usage", {}),
    )
