#!/usr/bin/env bash
# UserPromptSubmit hook (async): appends one line to the local prompt
# journal (otel/output/prompt_journal.jsonl, gitignored) correlating this
# prompt's text with the exact prompt_id OTel's own telemetry uses for the
# same turn (see specs/otel-collector-autostart.md §5). Best-effort and
# non-blocking: never fails the prompt submission, degrades gracefully if
# expected fields are missing.
set -uo pipefail

cd "$(dirname "$0")/../.." || exit 0

OUT_DIR="otel/output"
OUT_FILE="$OUT_DIR/prompt_journal.jsonl"

find_command() {
  command -v "$1" \
    || command -v "/opt/homebrew/bin/$1" \
    || command -v "/usr/local/bin/$1" 2>/dev/null
}

main() {
  local jq_bin
  if ! jq_bin=$(find_command jq); then
    printf 'log-prompt: jq not found; skipping this entry\n' >&2
    exit 0
  fi

  mkdir -p "$OUT_DIR" 2>/dev/null || exit 0

  local input
  input=$(cat)

  # `prompt_text` is not a confirmed field name — UserPromptSubmit's JSON
  # schema wasn't fully documented at implementation time (see spec's
  # "flagged as unverified" note). Try a couple of plausible field names
  # and fall back to null rather than guessing wrong silently; the journal
  # entry is still useful (prompt_id + timestamp) even with no text.
  local entry
  entry=$(printf '%s' "$input" | "$jq_bin" -c '{
    prompt_id: (.prompt_id // null),
    session_id: (.session_id // null),
    timestamp_iso: (now | todateiso8601),
    prompt_text: (.prompt // .prompt_text // .message // null)
  }') || exit 0

  printf '%s\n' "$entry" >> "$OUT_FILE" 2>/dev/null

  local has_text
  has_text=$(printf '%s' "$entry" | "$jq_bin" -r '.prompt_text != null')
  if [ "$has_text" != "true" ]; then
    printf 'log-prompt: no prompt text field found in hook input — logged prompt_id/session/timestamp only\n' >&2
  fi

  exit 0
}

main "$@"
