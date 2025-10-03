"""
Redis Cache Service
Handles caching for personality transformations and session state
REQ-PA-001: Cache transformed rationale (1-hour TTL)
"""

import json
import hashlib
from typing import Optional, Any
from redis.asyncio import Redis
from config.settings import settings


class CacheService:
    """
    Redis-based caching service for personality transformations and session data
    """

    def __init__(self):
        self.redis_client: Optional[Redis] = None

    async def connect(self):
        """Initialize Redis connection"""
        if not self.redis_client:
            try:
                self.redis_client = Redis.from_url(
                    settings.REDIS_URL,
                    password=settings.REDIS_PASSWORD,
                    decode_responses=True,
                    encoding="utf-8",
                )
                # Test connection
                await self.redis_client.ping()
            except Exception:
                # Silently fail - caching is optional
                self.redis_client = None

    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()

    async def get(self, key: str) -> Optional[dict]:
        """
        Retrieve cached value

        Args:
            key: Cache key

        Returns:
            Cached value as dict, or None if not found
        """
        try:
            if not self.redis_client:
                await self.connect()

            if not self.redis_client:
                return None  # Cache not available

            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
        except Exception:
            # Silently fail - return None
            pass
        return None

    async def set(
        self, key: str, value: dict, ttl: Optional[int] = None
    ) -> bool:
        """
        Store value in cache

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (default from settings)

        Returns:
            True if successful
        """
        try:
            if not self.redis_client:
                await self.connect()

            if not self.redis_client:
                return False  # Cache not available

            ttl = ttl or settings.REDIS_TTL_TRANSFORMATION
            serialized = json.dumps(value)
            await self.redis_client.setex(key, ttl, serialized)
            return True
        except Exception:
            # Silently fail
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete cached value

        Args:
            key: Cache key

        Returns:
            True if key existed and was deleted
        """
        if not self.redis_client:
            await self.connect()

        result = await self.redis_client.delete(key)
        return result > 0

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        if not self.redis_client:
            await self.connect()

        return await self.redis_client.exists(key) > 0

    def generate_transformation_key(
        self, rationale_id: str, style_params: dict
    ) -> str:
        """
        Generate deterministic cache key for personality transformation
        REQ-PA-001: Cache key based on rationale_id + style_params

        Args:
            rationale_id: UUID of neutral rationale
            style_params: Style parameters dict

        Returns:
            Cache key string
        """
        # Sort style_params for deterministic hash
        params_str = json.dumps(style_params, sort_keys=True)
        cache_input = f"{rationale_id}:{params_str}"
        cache_hash = hashlib.sha256(cache_input.encode()).hexdigest()

        return f"transformation:{cache_hash}"

    def generate_session_key(self, session_id: str) -> str:
        """
        Generate cache key for session data

        Args:
            session_id: UUID of negotiation session

        Returns:
            Cache key string
        """
        return f"session:{session_id}"

    async def get_transformation(
        self, rationale_id: str, style_params: dict
    ) -> Optional[dict]:
        """
        Retrieve cached personality transformation

        Args:
            rationale_id: UUID of neutral rationale
            style_params: Style parameters

        Returns:
            Cached transformation or None
        """
        key = self.generate_transformation_key(rationale_id, style_params)
        return await self.get(key)

    async def set_transformation(
        self, rationale_id: str, style_params: dict, transformation: dict
    ) -> bool:
        """
        Cache personality transformation

        Args:
            rationale_id: UUID of neutral rationale
            style_params: Style parameters
            transformation: Transformation data to cache

        Returns:
            True if successful
        """
        key = self.generate_transformation_key(rationale_id, style_params)
        return await self.set(key, transformation, ttl=settings.REDIS_TTL_TRANSFORMATION)

    async def get_session_state(self, session_id: str) -> Optional[dict]:
        """
        Retrieve session state from cache

        Args:
            session_id: UUID of negotiation session

        Returns:
            Session state or None
        """
        key = self.generate_session_key(session_id)
        return await self.get(key)

    async def set_session_state(
        self, session_id: str, state: dict
    ) -> bool:
        """
        Cache session state

        Args:
            session_id: UUID of negotiation session
            state: Session state to cache

        Returns:
            True if successful
        """
        key = self.generate_session_key(session_id)
        return await self.set(key, state, ttl=settings.REDIS_TTL_SESSION)

    async def invalidate_transformation_cache(self, rationale_id: str) -> int:
        """
        Invalidate all cached transformations for a rationale
        (e.g., when neutral rationale is updated)

        Args:
            rationale_id: UUID of neutral rationale

        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            await self.connect()

        # Find all transformation keys for this rationale
        pattern = f"transformation:*{rationale_id}*"
        keys = []
        async for key in self.redis_client.scan_iter(match=pattern):
            keys.append(key)

        if keys:
            return await self.redis_client.delete(*keys)
        return 0

    async def get_stats(self) -> dict:
        """
        Get cache statistics

        Returns:
            Dict with cache stats (hits, misses, memory, etc.)
        """
        if not self.redis_client:
            await self.connect()

        info = await self.redis_client.info("stats")
        return {
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "hit_rate": (
                info.get("keyspace_hits", 0)
                / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
            ),
            "memory_used": info.get("used_memory_human", "N/A"),
            "connected_clients": info.get("connected_clients", 0),
        }


# Global cache service instance
cache_service = CacheService()
