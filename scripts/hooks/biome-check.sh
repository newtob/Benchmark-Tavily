#!/usr/bin/env bash
# Runs biome lint and format check on TypeScript files
set -euo pipefail

if ! command -v pnpm &> /dev/null; then
  echo "pnpm not found; skipping biome check"
  exit 0
fi

if [ ! -f "ui/biome.json" ]; then
  echo "ui/biome.json not found; skipping biome check"
  exit 0
fi

cd ui || exit 1

if ! pnpm exec biome check . 2>&1; then
  echo "Biome check failed. Run: cd ui && pnpm exec biome check --fix ."
  exit 1
fi
