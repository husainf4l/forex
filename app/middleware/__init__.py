"""
Middleware package for the Gold Trading Dashboard
"""

from .error_handler import ErrorHandlerMiddleware
from .rate_limit import RateLimitMiddleware
from .cors import CORSMiddleware

__all__ = ["ErrorHandlerMiddleware", "RateLimitMiddleware", "CORSMiddleware"]
