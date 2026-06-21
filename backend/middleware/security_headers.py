from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    HTTP Middleware to add essential security headers to all HTTP responses.
    Protects against XSS, clickjacking, MIME-sniffing, and enforces HTTPS.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Prevent Clickjacking by denying frame options
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enforce legacy XSS protection in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Standardize referrer headers sent to other sites
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        
        # Strict-Transport-Security (STS) forces HTTPS connection
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        
        # Content-Security-Policy (CSP) headers restricting script / connect domains
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "connect-src 'self' http://localhost:3000 http://127.0.0.1:3000 http://localhost:8000 http://127.0.0.1:8000 https://*.vercel.app; "
            "img-src 'self' data: blob:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline';"
        )
        
        return response
