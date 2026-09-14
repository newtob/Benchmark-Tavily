"""HTTP routes for the benchmark table data. See specs/tavily-benchmark-app.md §4."""

from __future__ import annotations

from fastapi import APIRouter

from api.models.schemas import BenchmarkResponse
from api.services import fixtures

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness only — no downstream dependency check (a fixture-read
    failure would still fail *this* route via the exception it raises, but
    that's an orchestration/deploy problem, not something to mask here)."""
    return {"status": "ok"}


@router.get("/benchmark", response_model=BenchmarkResponse)
def benchmark() -> BenchmarkResponse:
    return fixtures.load_benchmark_response()
