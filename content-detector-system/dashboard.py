"""
Dashboard API router.
Endpoints:
    GET  /dashboard/stats    — aggregate counts, avg risk, pending reviews
    GET  /dashboard/recent   — last N analyses
    GET  /dashboard/queue    — review queue (pending by default)
    GET  /dashboard/health   — cache + worker status
"""

import logging

from fastapi import APIRouter, Depends, Query

from auth import get_current_user
from cache import cache
from database import get_recent_analyses, get_review_queue, get_stats
from workers import queue_size

logger = logging.getLogger("dashboard")

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_STATS_TTL = 60  # cache stats for 60 s


@router.get("/stats")
async def dashboard_stats(_user: dict = Depends(get_current_user)):
    cached = await cache.get("dashboard:stats")
    if cached:
        return cached
    stats = await get_stats()
    await cache.set("dashboard:stats", stats, ttl=_STATS_TTL)
    return stats


@router.get("/recent")
async def dashboard_recent(
    limit: int = Query(default=20, ge=1, le=100),
    _user: dict = Depends(get_current_user),
):
    return await get_recent_analyses(limit)


@router.get("/queue")
async def dashboard_queue(
    status: str = Query(default="pending", pattern="^(pending|reviewed)$"),
    _user: dict = Depends(get_current_user),
):
    return await get_review_queue(status)


@router.get("/health")
async def dashboard_health(_user: dict = Depends(get_current_user)):
    return {
        "cache": cache.info(),
        "worker_queue_depth": queue_size(),
    }
