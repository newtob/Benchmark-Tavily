# Prompt

Build a benchmarking app to measure the impact of the cost Tavily web search tool. 
This is built with a FastAPI backend (api/): GET /api/benchmark that compares Agent raw web search with Tavily, both CLI and Tavily MCP; against raw claude code web search. All tools will be compared with a fixed set of "web search queries". 

Each cell = tiktoken token count + $ price (at a stated reference model's per-token rate) of that response payload if fed to an LLM - not Tavily's own request pricing. 

Record real responses once via a script (with a TAVILY_API_KEY in `.env` file) as checked-in fixtures under api/fixtures/; default runtime, CI, and tests all replay fixtures - no live calls in CI.

SvelteKit + shadcn-svelte frontend (apps/ui) renders a 3-column table (Raw tool call, MCP) with "web search query" data-testid selectors. 

Package into one Dockerfile (nginx + uvicorn, single container, local-only, no compose). Playwright test asserts the table renders.

Two GitHub Actions: 
- fast_commit: lint/typecheck/unit-test etc., on commit
- full_pr: docker build, Playwright test, on PR
  
Build .gitignore/README/pre-commit for everything.
  
Write the plan to specs/ first; then implement, looping docker build + playwright until green.

## Design

The design has been completed in Claude Design: `@.\design_handoff_benchmark_tavily\`

## AgentSoul Memory

Location: `@C:\Users\newt0b\Code\Agent_Context\`

- A store of widely applicable decisions, conventions, and major architectural choices
- AgentSoul is it's own repo: update it's files directly.
- Follow `llm-wiki` pattern for pages and links, with OKF mardkwon format frontmatter that includses `type:`
- Before writing a /plan, search AgentSoul for prior knowledge, conventions, architecture patterns
- Update AgentSoul after every major decision and major implementation

Start here: `@C:\Users\newt0b\Code\Agent_Context\AgentSoul Index.md`

### Imports:

In addition to identifying relevant info following pages must be imported and actioned, likely in sub agents and implemented in seperate worktrees.
The following can be found linked in the `AgentSoul Index`:
- Python coding standards
- Logging conventions
- TypeScript Coding Standards
- Svelte Application Patterns
- fastapi patterns

- env file usage
- Ignore file policy
- Pre-commit hooks
- Testing Strategy
- Repository Workflow

Import and implement in sub agents:

- GitHub Actions Standards
- Dependency pinning
- Justfile usage
- Vercel Deployment
