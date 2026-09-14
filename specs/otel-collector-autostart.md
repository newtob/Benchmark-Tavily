# OTel Collector — Always-Running Spec

Status: **implemented** — built and verified end-to-end (collector
autostart via a cold `docker compose up -d --wait`-equivalent run, prompt
journal capture, and the cost/journal join) — see §4 addendum.
Scope: this repo's existing `otel/` per-prompt cost capture — collector
uptime (§1-4) plus a prompt-journal correlation/reporting layer (§5) —
unrelated to the Tavily-Benchmark app's own token/price comparisons (see
note in §0).

## 0. Not to be confused with the Tavily-Benchmark app

This spec is about capturing **Claude Code's own** per-prompt token/cost via
OpenTelemetry (`otel/parse_prompt_costs.py`, already in this repo). The
Tavily-Benchmark app planned in `specs/tavily-benchmark-app.md` separately
runs two unrelated cost comparisons — Tavily raw tool call vs MCP, and
Claude's web search tool vs Tavily's extract tool — each estimating the
LLM-token cost of a *tool response payload*. All of these involve
"tokens/price," but they measure different things and share no code — keep
that distinction in any docs this spec touches.

## 1. Problem

`otel/` already has everything needed to capture Claude Code's per-prompt
cost: `otel-collector-config.yaml`, `docker-compose.yml`, and
`.claude/settings.json` already sets the `OTEL_*` env vars unconditionally
(committed, not local-only — telemetry is already "on" by policy for anyone
in this repo). The one missing piece is that the **collector container
itself** is not guaranteed to be running:

- It only starts via a manual `just otel-up`.
- Nobody starting a fresh `claude` session in this repo is reminded to run
  it, so the exporter silently fails to send (connection refused to
  `localhost:4317`) until someone remembers.
- Two smaller gaps found while reviewing the existing config: the image tag
  is unpinned (`otel/opentelemetry-collector-contrib:latest`, violating this
  repo's own `dependency_pinning` convention), and the service has no
  `restart` policy or healthcheck, so a Docker daemon restart silently drops
  it with no signal.

Goal: the collector should be "already running" — self-starting, self-
healing, and pinned — with zero manual steps for a new contributor.

## 2. Target design

Use this repo's existing hook mechanism (`.claude/settings.json` already
runs a `TaskCompleted` hook) rather than a host-level launchd/systemd unit:
a **`SessionStart` hook**, committed (not `.local.json`), that ensures the
collector is up before the session does any work. This is portable (no
per-machine setup), self-documenting (lives in the repo), and — because
`SessionStart` fires early — gives even the *first* session after adding
this a working collector, not just the next one.

```text
claude session starts
  → SessionStart hook: scripts/hooks/otel-ensure-running.sh
      → docker compose -f otel/docker-compose.yml up -d --wait
      → best-effort: warn to stderr and continue on any failure, never
        block or fail the session over telemetry infrastructure
  → Claude Code's OTLP exporter (env vars already set repo-wide) now has
    a live collector to send to for this session
```

## 3. Changes

**`otel/docker-compose.yml`**

- Pin the image to an explicit version tag (verify the current stable tag
  on Docker Hub at implementation time — don't guess a version here).
- Add `restart: unless-stopped` so it survives a Docker daemon restart
  once started.
- Add a `healthcheck` once the config change below exposes something to
  check against.

**`otel/otel-collector-config.yaml`**

- Add the collector's built-in `health_check` extension so there's an
  actual endpoint to probe:

  ```yaml
  extensions:
    health_check:
      endpoint: 0.0.0.0:13133

  service:
    extensions: [health_check]
    pipelines:
      # unchanged
  ```

- Confirm at implementation time whether the `contrib` image has
  `wget`/`curl` available for the Compose `healthcheck.test` to exec
  against (verify via Context7/current docs or `docker run --rm -it
  <image> sh`); fall back to a raw TCP-connect check if neither is
  present.

**`scripts/hooks/otel-ensure-running.sh`** (new, same style as the existing
`secret-scan.sh`/`ts-typecheck.sh` wrappers):

- `cd` to the repo root, locate `docker` the same defensive way the
  existing hook scripts locate their tools.
- If Docker isn't installed or the daemon isn't reachable: print one clear
  warning line to stderr (e.g. "otel collector not started — Docker
  unavailable; per-prompt cost will not be captured this session") and
  `exit 0`. Never fail the hook over this — it must not block a session
  starting.
- Otherwise run `docker compose -f otel/docker-compose.yml up -d --wait`
  with a bounded timeout; on failure, same graceful warn-and-continue.

**`.claude/settings.json`** — add:

```json
"hooks": {
  "SessionStart": [
    { "hooks": [{ "type": "command", "command": "bash ./scripts/hooks/otel-ensure-running.sh" }] }
  ],
  "TaskCompleted": [ /* existing entry, unchanged */ ]
}
```

**`justfile`** — `otel-up` stays as the manual/troubleshooting entry point
(e.g. after `otel-down`, or on a machine where the hook's Docker check
failed); no behavior change needed there.

**Docs** — `agents.md` and `README.md`'s OTel sections get one line each:
the collector now auto-starts via a `SessionStart` hook, so the manual
`just otel-up` step described there is no longer required for the typical
flow (kept only as a manual recipe).

## 4. Verification

- Fresh clone, Docker running, no container up yet → open a `claude`
  session in the repo → `docker compose -f otel/docker-compose.yml ps`
  shows the collector `Up (healthy)` within the hook's `--wait` timeout.
- Stop the container manually (`just otel-down`), start a new session →
  it comes back on its own.
- Docker daemon not running → session starts normally, one warning line
  printed, no hard failure.
- `just otel-parse` / `just otel-costs` keep working unchanged once the
  container has been up during a session.

**Verified during implementation**: pinned to
`otel/opentelemetry-collector-contrib:0.160.0` (current stable at the
time). Confirmed empirically (not assumed) that this image ships no shell
at all — `docker run --entrypoint sh ...` fails with `exec: "sh": not
found` — validating the decision to check readiness from the host script
rather than an in-container `HEALTHCHECK`. `docker compose up -d` +
`otel-ensure-running.sh`'s host-side poll of `:13133/` were run end-to-end
from a cold state (no container running) and reached `Up (healthy)` /
HTTP 200 within a few seconds. `log-prompt.sh` and
`otel/join_prompt_journal.py` were both exercised with sample hook input
and sample `prompt_costs.json` data, including the "journal entry with no
matching cost row" edge case — all worked as designed.

## 5. Prompt Journal — correlating prompt text with `prompt_id`

### Problem

`otel/parse_prompt_costs.py` lists each prompt's cost keyed by `prompt_id`,
but nothing records what that prompt actually *was* — you get "prompt 7
cost $0.03" with no way to know what prompt 7 asked for.

### Mechanism

A new `UserPromptSubmit` hook, `scripts/hooks/log-prompt.sh` (`async:
true`, so it never blocks prompt submission), reads the hook's JSON stdin
and appends one line to `otel/output/prompt_journal.jsonl` — already
covered by the existing `otel/output/` `.gitignore` entry, so no
`.gitignore` change is needed — with:

- `prompt_id` — the hook's `prompt_id` field, confirmed via official docs
  to be the exact same UUID v4 as OTel's `prompt.id` attribute. This makes
  correlation **exact key matching, not chronological-order guessing.**
- `session_id`, `timestamp_iso`.
- `prompt_text`, **if** the hook payload actually exposes it. **Flagged as
  unverified**: whether `UserPromptSubmit`'s JSON input includes the raw
  prompt text at all (research came back unsure despite it being the
  hook's apparent purpose). The script must degrade gracefully — still log
  `prompt_id`/`session_id`/`timestamp_iso` if the text field is absent or
  named differently than expected, and warn once to stderr rather than
  fail or silently produce an empty journal.

### Summary field (v1: deterministic, no LLM call)

The "summarized intention" is a zero-cost, deterministic truncation of
`prompt_text` (first ~120 characters / first line) — **not** an
LLM-generated summary. An LLM summarization call would add cost and
complexity, and would itself generate more telemetry to track — a
circular dependency this spec avoids. A v2 idea (not required, not
implemented here): the agent optionally overwrites an entry with a better
one-line summary via a small update script, documented as a nice-to-have
rather than relied upon (an agent-must-remember-every-turn convention is
fragile).

### Correlating and reporting

`otel/join_prompt_journal.py` (new) left-joins `otel/output/
prompt_costs.json` (keyed by `prompt_id`) against `otel/output/
prompt_journal.jsonl` (keyed by the same `prompt_id`) and prints a combined
table (prompt index / cost / truncated text / summary), in the same style
as `parse_prompt_costs.py`'s existing stdout table. Handle the documented
edge case where a submitted prompt never produces a `claude_code.api_request`
event (e.g. hook-blocked) — such journal rows appear with null/zero cost
rather than being silently dropped.

### Changes

- **`.claude/settings.json`** — add `hooks.UserPromptSubmit` (running
  `scripts/hooks/log-prompt.sh`, `async: true`) alongside the
  `SessionStart` hook (§2/§3) and the existing `TaskCompleted` hook.
- **`justfile`** — new `otel-report` recipe: runs
  `otel/join_prompt_journal.py`.
- **Docs** — one line each in `agents.md`/`README.md` for `otel-report`
  and the journal file's purpose/location.

### Explicitly out of scope for this feature

- Any use of this data by, or correlation with, the Tavily-Benchmark app's
  token/price tables (`specs/tavily-benchmark-app.md`) — per §0's boundary,
  they share no code. That spec's own `claude_web_search.py` recording
  step deliberately unsets `OTEL_*`/`CLAUDE_CODE_ENABLE_TELEMETRY` on its
  `claude -p` subprocess calls specifically so its fixture-recording runs
  never appear in this journal.
- Real-time viewing/alerting — this is an offline join/report tool, run
  manually via `just otel-report`.

## 6. Out of scope

- Auto-starting Docker Desktop itself, or any host-level (launchd/systemd)
  persistence across machine reboots — the `SessionStart` hook only
  guarantees the container is up whenever a `claude` session in this repo
  begins, which is the actual requirement.
- Changing what `parse_prompt_costs.py` itself aggregates — this spec only
  adds collector *uptime* (§1-4) and a *separate* correlation/reporting
  layer on top (§5); it doesn't touch the aggregation logic.
