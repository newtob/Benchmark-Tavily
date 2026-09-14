#!/usr/bin/env bash
# Type-checks the root TypeScript project, then each workspace app that has
# its own tsconfig.json (currently apps/ui, checked via svelte-check since
# it understands .svelte files' script+template together, which plain tsc
# does not). Skips cleanly when there is no TS source yet; fails loudly
# when dependencies haven't been installed.
set -euo pipefail

cd "$(dirname "$0")/../.."

find_command() {
  command -v "$1" \
    || command -v "/opt/homebrew/bin/$1" \
    || command -v "/usr/local/bin/$1" \
    || command -v "$HOME/.local/bin/$1" 2>/dev/null
}

has_root_ts_files() {
  local f
  while IFS= read -r -d '' f; do
    case "$f" in
      *node_modules/*|*/dist/*|*/build/*|*/.next/*|apps/*|packages/*) continue ;;
      *) return 0 ;;
    esac
  done < <(find . \( -name '*.ts' -o -name '*.tsx' \) -print0 2>/dev/null)
  return 1
}

main() {
  local pnpm
  if ! pnpm=$(find_command pnpm); then
    echo "pnpm not found; cannot typecheck." >&2
    exit 127
  fi

  if has_root_ts_files; then
    if [[ ! -x node_modules/.bin/tsc ]]; then
      echo "TypeScript is not installed (node_modules/.bin/tsc missing)." >&2
      echo "Run 'just ts-install' (or 'pnpm install') first." >&2
      exit 1
    fi
    "$pnpm" exec tsc --noEmit -p tsconfig.json
  else
    echo "No root .ts/.tsx files yet; skipping root typecheck."
  fi

  if [[ -f apps/ui/package.json ]]; then
    if [[ ! -d apps/ui/node_modules ]]; then
      echo "apps/ui dependencies are not installed; cannot typecheck." >&2
      echo "Run 'pnpm install' first." >&2
      exit 1
    fi
    (cd apps/ui && "$pnpm" exec svelte-kit sync && "$pnpm" exec svelte-check --tsconfig ./tsconfig.json)
  fi
}

main "$@"
