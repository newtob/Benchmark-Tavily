#!/usr/bin/env bash
# Runs the required staged secret scan with betterleaks or a gitleaks fallback.
set -euo pipefail

find_command() {
  command -v "$1" \
    || command -v "/opt/homebrew/bin/$1" \
    || command -v "/usr/local/bin/$1" \
    || command -v "$HOME/.local/bin/$1" \
    || command -v "$HOME/.cargo/bin/$1" \
    || command -v "/c/ProgramData/chocolatey/bin/$1" \
    || command -v "$USERPROFILE/scoop/shims/$1.exe" \
    || command -v "$LOCALAPPDATA/Microsoft/WinGet/Links/$1.exe" \
    || command -v "/c/Program Files/$1/$1.exe" 2>/dev/null
}

main() {
  local betterleaks
  local gitleaks

  if betterleaks=$(find_command betterleaks); then
    exec "$betterleaks"
  fi

  if gitleaks=$(find_command gitleaks); then
    exec "$gitleaks" git --redact=80 --no-banner --timeout 2 -v --max-target-megabytes=2 --pre-commit --staged
  fi

  printf '%s\n' 'Neither betterleaks nor gitleaks is installed; cannot run the required secret scan.' >&2
  exit 127
}

main "$@"
