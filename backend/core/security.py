import time
import secrets
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from passlib.context import CryptContext
from bson import ObjectId

from .config import settings
from .database import get_db

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme definition
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)


# --- Sliding Window Rate Limiter ---
class RateLimiter:
    """In-memory sliding-window rate limiter mapping client IPs to timestamps."""
    def __init__(self, requests_limit: int, window_seconds: int):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.history = defaultdict(list)

    def is_rate_limited(self, ip: str) -> bool:
        now = time.time()
        # Clean expired timestamps
        self.history[ip] = [t for t in self.history[ip] if now - t < self.window_seconds]
        if len(self.history[ip]) >= self.requests_limit:
            return True
        self.history[ip].append(now)
        return False


# Rate limit: 5 requests per 10 seconds for auth endpoints
auth_limiter = RateLimiter(requests_limit=5, window_seconds=10)


async def rate_limit_auth(request: Request):
    """FastAPI dependency to rate limit actions."""
    ip = request.client.host if request.client else "unknown_ip"
    if auth_limiter.is_rate_limited(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many request attempts. Please try again in a moment."
        )


# --- Token operations ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generates a bcrypt hash for a plain password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed short-lived JWT Access Token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Use configured expiry from .env (ACCESS_TOKEN_EXPIRE_MINUTES, default 1440 = 24h)
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt

def create_refresh_token() -> str:
    """Generates a secure random refresh token string."""
    return secrets.token_hex(32)

async def get_current_user(request: Request, token: str = Depends(oauth2_scheme), db: Any = Depends(get_db)):
    """FastAPI dependency to extract and authorize the user session from a JWT bearer token.
    
    Falls back to the demo user ONLY in development/testing mode when no token is provided.
    Raises HTTPException (401) immediately for any invalid/expired token, or if running in production.
    """
    # Allow token retrieval via query parameter (e.g. for PDF downloads)
    if not token:
        token = request.query_params.get("token")

    if token:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            email: str = payload.get("sub")
            token_type: str = payload.get("type", "access")
            if email and token_type == "access":
                user = await db["users"].find_one({"email": email})
                if user:
                    user["id"] = str(user["_id"])
                    return user
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User associated with this token was not found."
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type."
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired. Please log in again."
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token credentials."
            )

    # In production, we MUST reject requests without a valid token
    if settings.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided."
        )

    # No token in non-production: resolve or auto-create the demo user
    demo_user = await db["users"].find_one({"email": "demo@ecopilot.ai"})
    if demo_user:
        demo_user["id"] = str(demo_user["_id"])
        return demo_user

    demo_user = {
        "email": "demo@ecopilot.ai",
        "password_hash": get_password_hash("password123"),
        "full_name": "EcoPilot Demo User",
        "created_at": datetime.now(timezone.utc),
        "profile": {
            "country": "US",
            "diet_preference": "vegetarian",
            "household_size": 2,
            "has_car": True
        }
    }
    res = await db["users"].insert_one(demo_user)
    demo_user["id"] = str(res.inserted_id)
    return demo_user
