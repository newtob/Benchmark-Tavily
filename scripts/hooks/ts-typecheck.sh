#!/usr/bin/env bash
# Type-checks the TypeScript project, skipping cleanly when there is no TS
# source yet and failing loudly when dependencies haven't been installed.
set -euo pipefail

cd "$(dirname "$0")/../.."

find_command() {
  command -v "$1" \
    || command -v "/opt/homebrew/bin/$1" \
    || command -v "/usr/local/bin/$1" \
    || command -v "$HOME/.local/bin/$1" 2>/dev/null
}

has_ts_files() {
  local f
  while IFS= read -r -d '' f; do
    case "$f" in
      *node_modules/*|*/dist/*|*/build/*|*/.next/*) continue ;;
      *) return 0 ;;
    esac
  done < <(find . \( -name '*.ts' -o -name '*.tsx' \) -print0 2>/dev/null)
  return 1
}

main() {
  if ! has_ts_files; then
    echo "No .ts/.tsx files yet; skipping typecheck."
    exit 0
  fi

  local pnpm
  if ! pnpm=$(find_command pnpm); then
    echo "pnpm not found; cannot typecheck." >&2
    exit 127
  fi

  if [[ ! -x node_modules/.bin/tsc ]]; then
    echo "TypeScript is not installed (node_modules/.bin/tsc missing)." >&2
    echo "Run 'just ts-install' (or 'pnpm install') first." >&2
    exit 1
  fi

  "$pnpm" exec tsc --noEmit -p tsconfig.json
}

main "$@"
