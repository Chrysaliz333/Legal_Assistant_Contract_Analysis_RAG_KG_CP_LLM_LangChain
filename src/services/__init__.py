"""Business logic services for Legal Assistant Multi-Session Continuity System"""

# Import only essential services (cache_service requires Redis which is optional)
try:
    from .cache_service import CacheService
    _has_cache = True
except ImportError:
    _has_cache = False
    CacheService = None

from .embedding_service import EmbeddingService

__all__ = [
    "CacheService",
    "EmbeddingService",
]
