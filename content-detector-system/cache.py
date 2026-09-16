"""
Cache layer: Redis when available, in-memory dict fallback otherwise.
Usage:
    cache = Cache()
    await cache.get("key")
    await cache.set("key", value, ttl=300)
    await cache.delete("key")
"""

import json
import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger("cache")

_REDIS_URL = os.environ.get("REDIS_URL", "")  # e.g. redis://localhost:6379/0


class _MemoryBackend:
    """Thread-safe in-memory cache with TTL."""

    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)

    async def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at and time.time() > expires_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        self._store[key] = (value, time.time() + ttl if ttl else 0)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def flush(self) -> None:
        self._store.clear()

    def info(self) -> dict:
        return {"backend": "memory", "keys": len(self._store)}


class _RedisBackend:
    def __init__(self, client):
        self._r = client

    async def get(self, key: str) -> Optional[Any]:
        raw = await self._r.get(key)
        return json.loads(raw) if raw is not None else None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        await self._r.set(key, json.dumps(value), ex=ttl or None)

    async def delete(self, key: str) -> None:
        await self._r.delete(key)

    async def flush(self) -> None:
        await self._r.flushdb()

    def info(self) -> dict:
        return {"backend": "redis", "url": _REDIS_URL}


class Cache:
    """
    Unified cache interface.
    Automatically uses Redis if REDIS_URL env var is set and redis[asyncio] is installed,
    otherwise falls back to in-memory.
    """

    def __init__(self):
        self._backend = None  # lazy-initialised on first use

    async def _get_backend(self):
        if self._backend is not None:
            return self._backend
        if _REDIS_URL:
            try:
                import redis.asyncio as aioredis
                client = aioredis.from_url(_REDIS_URL, decode_responses=True)
                await client.ping()
                self._backend = _RedisBackend(client)
                logger.info("Cache: connected to Redis at %s", _REDIS_URL)
            except Exception as e:
                logger.warning("Redis unavailable (%s) — using in-memory cache", e)
                self._backend = _MemoryBackend()
        else:
            self._backend = _MemoryBackend()
            logger.info("Cache: using in-memory backend (set REDIS_URL to use Redis)")
        return self._backend

    async def get(self, key: str) -> Optional[Any]:
        return await (await self._get_backend()).get(key)

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        await (await self._get_backend()).set(key, value, ttl)

    async def delete(self, key: str) -> None:
        await (await self._get_backend()).delete(key)

    def info(self) -> dict:
        if self._backend is None:
            return {"backend": "uninitialised"}
        return self._backend.info()


# Singleton used across the app
cache = Cache()
