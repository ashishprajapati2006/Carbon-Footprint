import time
import threading
from typing import Any, Optional


class InMemoryCache:
    """
    Lightweight, thread-safe in-memory cache with Time-To-Live (TTL) support.
    Useful for caching expensive API responses like Google Gemini.
    """
    def __init__(self, default_ttl: int = 600):
        self._cache = {}
        self._default_ttl = default_ttl
        self._lock = threading.Lock()

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Sets a value in the cache with an expiration timestamp."""
        expiry = time.time() + (ttl if ttl is not None else self._default_ttl)
        with self._lock:
            self._cache[key] = (value, expiry)

    def get(self, key: str) -> Optional[Any]:
        """Retrieves a value from the cache. Returns None if key is missing or expired."""
        with self._lock:
            if key not in self._cache:
                return None
            value, expiry = self._cache[key]
            if time.time() > expiry:
                # Cache expired, clean up
                del self._cache[key]
                return None
            return value

    def delete(self, key: str) -> None:
        """Removes a key from the cache if it exists."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self) -> None:
        """Clears all cached items."""
        with self._lock:
            self._cache.clear()


# Global instance for caching sustainability assessments
assessment_cache = InMemoryCache(default_ttl=600)
