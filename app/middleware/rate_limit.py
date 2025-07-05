"""
Rate limiting middleware
"""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

from ..core.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware"""

    def __init__(self, app, calls_per_minute: int = 60):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.client_requests = {}

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/docs", "/redoc"]:
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Clean old entries
        cutoff_time = current_time - 60  # 1 minute ago
        if client_ip in self.client_requests:
            self.client_requests[client_ip] = [
                req_time
                for req_time in self.client_requests[client_ip]
                if req_time > cutoff_time
            ]

        # Check rate limit
        if client_ip not in self.client_requests:
            self.client_requests[client_ip] = []

        if len(self.client_requests[client_ip]) >= self.calls_per_minute:
            logger.warning(f"⚠️ Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "limit": self.calls_per_minute,
                    "window": "1 minute",
                },
            )

        # Add current request
        self.client_requests[client_ip].append(current_time)

        return await call_next(request)
