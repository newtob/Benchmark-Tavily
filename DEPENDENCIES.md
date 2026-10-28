# Dependencies

Direct dependencies only (every one pinned to an explicit version, per this
repo's dependency-pinning convention). Full resolved dependency graphs,
including transitive packages, are locked in `uv.lock` (Python) and
`pnpm-lock.yaml` (TypeScript/JavaScript).

## Docker images

| Image | Used in | Purpose |
| --- | --- | --- |
| `node:22.23.2-bookworm-slim` | `Dockerfile` (`ui-build` stage) | Builds the SvelteKit static frontend |
| `python:3.15.2-slim-bookworm` | `Dockerfile` (`python-deps` + `runtime` stages) | Installs Python deps and runs the FastAPI backend |
| `otel/opentelemetry-collector-contrib:0.160.0` | `otel/docker-compose.yml` | OTel collector (per-prompt Claude Code cost capture) |

`Dockerfile.vercel` is a symlink to `Dockerfile` (Vercel Container deploy
mode) — same images, no separate entry.

## Python (`pyproject.toml`)

### Runtime dependencies

| Package | Version |
| --- | --- |
| fastapi | 0.141.1 |
| uvicorn[standard] | 0.52.4 |
| tavily-python | 0.8.2 |
| httpx | 0.28.1 |
| mcp | 2.2.0 |
| tiktoken | 0.14.0 |
| pyyaml | 6.0.3 |

### Dev dependencies

| Package | Version |
| --- | --- |
| ruff | 0.16.7 |
| mypy | 2.3.1 |
| pytest | 9.1.1 |
| prek | 0.5.2 |
| respx | 0.23.1 |
| types-PyYAML | 6.0.12.20260906 |

## TypeScript / JavaScript

Three `package.json` files (pnpm workspace: `apps/*`, `packages/*`, `e2e`).

### Root `package.json` — repo tooling

| Package | Version | Type |
| --- | --- | --- |
| zod | 4.6.2 | dependency |
| @biomejs/biome | 2.5.13 | dev |
| @total-typescript/ts-reset | 0.6.1 | dev |
| @types/node | 22.20.2 | dev |
| typescript | 7.0.2 | dev |
| vitest | 5.0.0 | dev |

### `apps/ui/package.json` — SvelteKit frontend

| Package | Version | Type |
| --- | --- | --- |
| @fontsource-variable/figtree | 5.3.0 | dependency |
| @fontsource-variable/oxanium | 5.3.0 | dependency |
| class-variance-authority | 0.7.1 | dependency |
| cn | 0.3.0 | dependency |
| tw-animate-css | 1.4.0 | dependency |
| @sveltejs/adapter-static | 3.0.10 | dev |
| @sveltejs/kit | 2.70.3 | dev |
| @sveltejs/vite-plugin-svelte | 7.3.0 | dev |
| @tailwindcss/vite | 4.3.3 | dev |
| @types/node | 22.20.2 | dev |
| shadcn | 4.21.0 | dev |
| svelte | 5.57.0 | dev |
| svelte-check | 4.7.6 | dev |
| tailwindcss | 4.3.3 | dev |
| typescript | **6.0.3** | dev |
| vite | 8.3.0 | dev |

`typescript` is pinned separately from the root's `7.0.2` — a documented
compatibility hold, since `svelte-check`/`@sveltejs/kit` don't yet support
TypeScript 7 without a separate dual-version setup (see
`specs/tavily-benchmark-app.md` §7).

### `e2e/package.json` — Playwright tests

| Package | Version | Type |
| --- | --- | --- |
| @playwright/test | 1.63.0 | dev |
| @types/node | 22.20.2 | dev |
