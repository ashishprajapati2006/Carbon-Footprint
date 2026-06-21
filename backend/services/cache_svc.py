"""
In-Memory Cache Service — Token-Efficient Response Caching for Carbon AI Features.

Provides a lightweight, thread-safe TTL cache to avoid redundant calls to the
Google Gemini API, reducing token consumption and API costs for the EcoPilot
sustainability platform. Frequently repeated carbon assessment prompts, room
audit responses, and chat completions are cached to improve response latency.
"""
import time
import threading
from typing import Any, Optional

# Named TTL constants (seconds)
_DEFAULT_CACHE_TTL_SECONDS: int = 600      # 10 minutes — general cache default
_ASSESSMENT_CACHE_TTL_SECONDS: int = 600   # 10 minutes — sustainability assessment results


class InMemoryCache:
    """
    Lightweight, thread-safe in-memory cache with Time-To-Live (TTL) support.

    Used across the EcoPilot platform to cache expensive AI responses:
      - Sustainability habit assessments from Gemini
      - Carbon twin simulation results
      - Chat history summaries for token optimization

    Thread safety is guaranteed via a threading.Lock for concurrent FastAPI workers.
    """
    def __init__(self, default_ttl: int = _DEFAULT_CACHE_TTL_SECONDS):
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
assessment_cache = InMemoryCache(default_ttl=_ASSESSMENT_CACHE_TTL_SECONDS)
