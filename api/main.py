"""Composition root. See specs/tavily-benchmark-app.md §4."""

from __future__ import annotations

from fastapi import FastAPI

from api.routers import benchmark

app = FastAPI(title="Tavily Benchmark API")
app.include_router(benchmark.router, prefix="/api")
