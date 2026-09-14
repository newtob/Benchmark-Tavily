# OTel Collector — Always-Running Spec

Status: **draft plan, not yet implemented**
Scope: this repo's existing `otel/` per-prompt cost capture, unrelated to the Tavily-Benchmark app's own token/price table (see note in §0).

## 0. Not to be confused with the Tavily-Benchmark app

This spec is about capturing **Claude Code's own** per-prompt token/cost via OpenTelemetry (`otel/parse_prompt_costs.py`, already in this repo). The Tavily-Benchmark app planned in `specs/tavily-benchmark-app.md` separately estimates the LLM-token cost of a *Tavily response payload*. Both involve "tokens/price," but they measure different things and share no code — keep that distinction in any docs this spec touches.

## 1. Problem

`otel/` already has everything needed to capture Claude Code's per-prompt cost: `otel-collector-config.yaml`, `docker-compose.yml`, and `.claude/settings.json` already sets the `OTEL_*` env vars unconditionally (committed, not local-only — telemetry is already "on" by policy for anyone in this repo). The one missing piece is that the **collector container itself** is not guaranteed to be running:

- It only starts via a manual `just otel-up`.
- Nobody starting a fresh `claude` session in this repo is reminded to run it, so the exporter silently fails to send (connection refused to `localhost:4317`) until someone remembers.
- Two smaller gaps found while reviewing the existing config: the image tag is unpinned (`otel/ opentelemetry-collector-contrib:latest`, violating this repo's own `dependency_pinning` convention), and the service has no `restart` policy or healthcheck, so a Docker daemon restart silently drops it with no signal.

Goal: the collector should be "already running" — self-starting, self-healing, and pinned — with zero manual steps for a new contributor.

## 2. Target design

Use this repo's existing hook mechanism (`.claude/settings.json` already runs a `TaskCompleted` hook) rather than a host-level launchd/systemd unit:
a **`SessionStart` hook**, committed (not `.local.json`), that ensures the collector is up before the session does any work. This is portable (no per-machine setup), self-documenting (lives in the repo), and — because `SessionStart` fires early — gives even the *first* session after adding this a working collector, not just the next one.

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

- Pin the image to an explicit version tag (verify the current stable tag on Docker Hub at implementation time — don't guess a version here).
- Add `restart: unless-stopped` so it survives a Docker daemon restart once started.
- Add a `healthcheck` once the config change below exposes something to check against.

**`otel/otel-collector-config.yaml`**

- Add the collector's built-in `health_check` extension so there's an actual endpoint to probe:

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

## 5. Out of scope

- Auto-starting Docker Desktop itself, or any host-level (launchd/systemd)
  persistence across machine reboots — the `SessionStart` hook only
  guarantees the container is up whenever a `claude` session in this repo
  begins, which is the actual requirement.
- Changing what gets captured or how `parse_prompt_costs.py` aggregates it
  — this spec only addresses collector *uptime*.
