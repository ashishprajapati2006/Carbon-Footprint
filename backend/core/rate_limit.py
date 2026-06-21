import time
import threading
from typing import Dict, List
from fastapi import HTTPException, status, Depends
from core.security import get_current_user


class InMemoryRateLimiter:
    """
    In-memory rate limiter using a sliding window log algorithm.
    Thread-safe and designed to be used as a FastAPI dependency.
    """
    def __init__(self, requests_limit: int = 5, window_seconds: int = 60):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        # Maps user_id string to a list of request timestamps
        self.user_requests: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def __call__(self, current_user: dict = Depends(get_current_user)):
        user_id = str(current_user["id"])
        now = time.time()
        
        with self._lock:
            # Clean up old timestamps outside the window
            if user_id not in self.user_requests:
                self.user_requests[user_id] = []
                
            timestamps = self.user_requests[user_id]
            cutoff = now - self.window_seconds
            # Keep only timestamps within the current window
            valid_timestamps = [t for t in timestamps if t > cutoff]
            self.user_requests[user_id] = valid_timestamps
            
            if len(valid_timestamps) >= self.requests_limit:
                # Return the time remaining until a slot opens up
                oldest_timestamp = valid_timestamps[0]
                retry_after = int(self.window_seconds - (now - oldest_timestamp))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "message": "Too many sustainability assessments. Please try again later.",
                        "retry_after_seconds": max(1, retry_after)
                    }
                )
                
            # Log the current request
            self.user_requests[user_id].append(now)


# Create assessment rate limiter instance: limit to 5 assessments per minute
assessment_rate_limiter = InMemoryRateLimiter(requests_limit=5, window_seconds=60)
