import os
import pytest

# Enforce testing environment variables globally for all test suites
os.environ["MONGODB_URI"] = "dummy"
os.environ["GEMINI_API_KEY"] = "dummy_api_key"

@pytest.fixture(autouse=True)
def clear_rate_limiters():
    """Autouse fixture to clear rate limiter history before each test runs to avoid rate-limiting leakage."""
    try:
        from core.security import auth_limiter
        auth_limiter.history.clear()
    except Exception:
        pass

    try:
        from core.rate_limit import assessment_rate_limiter
        assessment_rate_limiter.user_requests.clear()
    except Exception:
        pass
