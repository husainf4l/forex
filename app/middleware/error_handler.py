"""
Error handling middleware
"""

import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..core.logging import get_logger

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to handle errors and add request logging"""

    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Start timing
        start_time = time.time()

        # Log request
        logger.info(
            f"🔍 [{request_id}] {request.method} {request.url.path} - "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"✅ [{request_id}] {response.status_code} - "
                f"Duration: {duration:.3f}s"
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time

            # Log error
            logger.error(
                f"❌ [{request_id}] Error: {str(e)} - " f"Duration: {duration:.3f}s"
            )

            # Return error response
            if isinstance(e, StarletteHTTPException):
                return JSONResponse(
                    status_code=e.status_code,
                    content={
                        "error": e.detail,
                        "request_id": request_id,
                        "timestamp": time.time(),
                    },
                )
            else:
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Internal server error",
                        "request_id": request_id,
                        "timestamp": time.time(),
                    },
                )
