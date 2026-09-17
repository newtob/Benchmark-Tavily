from __future__ import annotations

from api.routers.benchmark import router as benchmark_router
from api.routers.searches import router as searches_router

__all__ = [
    "benchmark_router",
    "searches_router",
]
