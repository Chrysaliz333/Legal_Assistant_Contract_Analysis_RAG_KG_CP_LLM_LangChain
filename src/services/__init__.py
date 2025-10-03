"""Business logic services for Legal Assistant Multi-Session Continuity System"""

from .cache_service import CacheService
from .embedding_service import EmbeddingService

__all__ = [
    "CacheService",
    "EmbeddingService",
]
