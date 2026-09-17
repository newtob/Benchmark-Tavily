"""Searches listing endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from api.models.schemas import SearchQuery
from api.services import load_searches

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["searches"])


@router.get("/searches", response_model=list[SearchQuery])
async def get_searches() -> list[SearchQuery]:
    """Get the fixed benchmark search queries.

    Returns:
        List of SearchQuery objects (query, note, successfuly_return_includes)
        loaded from searches.yaml.

    Raises:
        HTTPException: If searches.yaml cannot be loaded.
    """
    try:
        return load_searches()
    except FileNotFoundError as e:
        logger.error(f"Failed to load searches: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Searches unavailable: {e}",
        ) from e
