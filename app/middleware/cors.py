"""
CORS middleware
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class CORSMiddleware(BaseHTTPMiddleware):
    """CORS middleware for handling cross-origin requests"""

    def __init__(self, app, allow_origins: list = None):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            # Handle preflight requests
            response = Response()
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = (
                "GET, POST, PUT, DELETE, OPTIONS"
            )
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization"
            )
            response.headers["Access-Control-Max-Age"] = "86400"
            return response

        response = await call_next(request)

        # Add CORS headers
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"

        return response
