#!/usr/bin/env bash
# Runs secret detection with betterleaks or gitleaks fallback
set -euo pipefail

find_command() {
  local tool="$1"

  # Try direct command lookup (PATH)
  if command -v "$tool" 2>/dev/null; then
    return 0
  fi

  # On Windows, try using cmd.exe to find the tool via Windows PATH
  if command -v cmd.exe &>/dev/null; then
    local windows_path
    windows_path=$(cmd.exe /c "for %i in ($tool.exe) do @echo %~\$PATH:i" 2>/dev/null | tr -d '\r' | head -1)
    if [ -n "$windows_path" ] && [ -x "$windows_path" ]; then
      echo "$windows_path"
      return 0
    fi
  fi

  # macOS Homebrew paths
  [ -x "/opt/homebrew/bin/$tool" ] && echo "/opt/homebrew/bin/$tool" && return 0
  [ -x "/usr/local/bin/$tool" ] && echo "/usr/local/bin/$tool" && return 0

  # Unix-like paths
  [ -x "$HOME/.local/bin/$tool" ] && echo "$HOME/.local/bin/$tool" && return 0
  [ -x "$HOME/.cargo/bin/$tool" ] && echo "$HOME/.cargo/bin/$tool" && return 0

  # Windows Chocolatey paths
  [ -x "/c/ProgramData/chocolatey/bin/$tool.exe" ] && echo "/c/ProgramData/chocolatey/bin/$tool.exe" && return 0
  [ -x "/c/ProgramData/chocolatey/bin/$tool.EXE" ] && echo "/c/ProgramData/chocolatey/bin/$tool.EXE" && return 0

  # Windows Scoop paths - convert backslashes to forward slashes
  if [ -n "${USERPROFILE:-}" ]; then
    local userprofile="${USERPROFILE//\\//}"
    [ -x "$userprofile/scoop/shims/$tool.exe" ] && echo "$userprofile/scoop/shims/$tool.exe" && return 0
    [ -x "$userprofile/scoop/shims/$tool.EXE" ] && echo "$userprofile/scoop/shims/$tool.EXE" && return 0
    [ -x "$userprofile/scoop/apps/$tool/current/$tool.exe" ] && echo "$userprofile/scoop/apps/$tool/current/$tool.exe" && return 0
    [ -x "$userprofile/scoop/apps/$tool/current/$tool.EXE" ] && echo "$userprofile/scoop/apps/$tool/current/$tool.EXE" && return 0
  fi

  # Windows WinGet paths - convert backslashes to forward slashes
  if [ -n "${LOCALAPPDATA:-}" ]; then
    local localappdata="${LOCALAPPDATA//\\//}"
    [ -x "$localappdata/Microsoft/WinGet/Links/$tool.exe" ] && echo "$localappdata/Microsoft/WinGet/Links/$tool.exe" && return 0
    [ -x "$localappdata/Microsoft/WinGet/Links/$tool.EXE" ] && echo "$localappdata/Microsoft/WinGet/Links/$tool.EXE" && return 0
  fi

  # Windows Program Files paths
  [ -x "/c/Program Files/$tool/$tool.exe" ] && echo "/c/Program Files/$tool/$tool.exe" && return 0
  [ -x "/c/Program Files/$tool/$tool.EXE" ] && echo "/c/Program Files/$tool/$tool.EXE" && return 0
  [ -x "/c/Program Files (x86)/$tool/$tool.exe" ] && echo "/c/Program Files (x86)/$tool/$tool.exe" && return 0
  [ -x "/c/Program Files (x86)/$tool/$tool.EXE" ] && echo "/c/Program Files (x86)/$tool/$tool.EXE" && return 0

  # Windows user local paths - convert backslashes to forward slashes
  if [ -n "${LOCALAPPDATA:-}" ]; then
    local localappdata="${LOCALAPPDATA//\\//}"
    [ -x "$localappdata/Programs/$tool/$tool.exe" ] && echo "$localappdata/Programs/$tool/$tool.exe" && return 0
    [ -x "$localappdata/Programs/$tool/$tool.EXE" ] && echo "$localappdata/Programs/$tool/$tool.EXE" && return 0
  fi

  return 1
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
