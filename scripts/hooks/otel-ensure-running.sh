#!/usr/bin/env bash
# SessionStart hook: makes sure the OTel collector (otel/docker-compose.yml)
# is up before the session does any work, so Claude Code's own per-prompt
# telemetry has somewhere to land from the very first prompt onward. Never
# blocks or fails a session over this — telemetry infrastructure is a nice-
# to-have, not a session dependency. See specs/otel-collector-autostart.md.
set -uo pipefail

cd "$(dirname "$0")/../.." || exit 0

WARN() { printf 'otel: %s\n' "$1" >&2; }

find_command() {
  command -v "$1" \
    || command -v "/opt/homebrew/bin/$1" \
    || command -v "/usr/local/bin/$1" \
    || command -v "$HOME/.local/bin/$1" 2>/dev/null
}

main() {
  local docker_bin
  if ! docker_bin=$(find_command docker); then
    WARN "collector not started — Docker not found; per-prompt cost will not be captured this session"
    exit 0
  fi

  if ! "$docker_bin" info >/dev/null 2>&1; then
    WARN "collector not started — Docker daemon not reachable; per-prompt cost will not be captured this session"
    exit 0
  fi

  if ! "$docker_bin" compose -f otel/docker-compose.yml up -d >/dev/null 2>&1; then
    WARN "collector failed to start via 'docker compose up -d' — per-prompt cost will not be captured this session"
    exit 0
  fi

  # The collector image has no shell/wget/curl to run a container-level
  # HEALTHCHECK against (see otel/docker-compose.yml), so readiness is
  # checked from here instead, against the health_check extension's HTTP
  # endpoint. Best-effort: a slow-starting collector just means this
  # session's earliest prompts might not be captured, not a hard failure.
  local curl_bin waited=0
  if curl_bin=$(find_command curl); then
    while [ "$waited" -lt 15 ]; do
      if "$curl_bin" -sf -o /dev/null "http://localhost:13133/"; then
        exit 0
      fi
      sleep 1
      waited=$((waited + 1))
    done
    WARN "collector did not report healthy within 15s — it may still come up shortly"
  fi

  exit 0
}

main "$@"
