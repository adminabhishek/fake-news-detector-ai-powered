import time
import hashlib
import logging
from typing import Any, Optional
from config import CACHE_TTL_SECONDS, CACHE_MAX_SIZE

logger = logging.getLogger(__name__)

class TTLCache:
    """
    Simple TTL-based in-memory cache
    """
    def __init__(self, ttl_seconds: int = CACHE_TTL_SECONDS, max_size: int = CACHE_MAX_SIZE):
        self.cache = {}
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        logger.info(f"Initialized TTL cache with TTL={ttl_seconds}s, max_size={max_size}")

    def _get_key(self, key: str) -> str:
        """Generate a hash key for consistent storage"""
        return hashlib.md5(key.encode()).hexdigest()

    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            k for k, v in self.cache.items()
            if current_time - v['timestamp'] > self.ttl_seconds
        ]
        for key in expired_keys:
            del self.cache[key]
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def _enforce_max_size(self):
        """Enforce maximum cache size by removing oldest entries"""
        if len(self.cache) >= self.max_size:
            # Remove oldest entries (simple FIFO)
            sorted_items = sorted(self.cache.items(), key=lambda x: x[1]['timestamp'])
            to_remove = len(self.cache) - self.max_size + 10  # Remove extra to avoid frequent cleanup
            for key, _ in sorted_items[:to_remove]:
                del self.cache[key]
            logger.debug(f"Enforced max cache size, removed {to_remove} entries")

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        cache_key = self._get_key(key)
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if time.time() - entry['timestamp'] <= self.ttl_seconds:
                logger.debug(f"Cache hit for key: {key[:50]}...")
                return entry['value']
            else:
                # Remove expired entry
                del self.cache[cache_key]
                logger.debug(f"Cache miss (expired) for key: {key[:50]}...")

        logger.debug(f"Cache miss for key: {key[:50]}...")
        return None

    def set(self, key: str, value: Any):
        """Set value in cache"""
        self._cleanup_expired()
        self._enforce_max_size()

        cache_key = self._get_key(key)
        self.cache[cache_key] = {
            'value': value,
            'timestamp': time.time()
        }
        logger.debug(f"Cached value for key: {key[:50]}...")

    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        logger.info("Cache cleared")

    def size(self) -> int:
        """Get current cache size"""
        self._cleanup_expired()
        return len(self.cache)

    def stats(self) -> dict:
        """Get cache statistics"""
        self._cleanup_expired()
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'ttl_seconds': self.ttl_seconds
        }

# Global cache instances
search_cache = TTLCache()
article_cache = TTLCache()

def get_search_cache():
    """Get the search results cache"""
    return search_cache

def get_article_cache():
    """Get the article content cache"""
    return article_cache

def clear_all_caches():
    """Clear all caches"""
    search_cache.clear()
    article_cache.clear()
    logger.info("All caches cleared")
