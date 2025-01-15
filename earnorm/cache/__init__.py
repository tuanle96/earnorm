"""
Cache module for EarnORM providing Redis-based caching functionality.
"""

from earnorm.cache.core.manager import CacheManager
from earnorm.cache.decorators.cached import cached

__all__ = ["CacheManager", "cached"]
