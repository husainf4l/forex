"""
Gold Trading Dashboard - Main Application
Professional async FastAPI application with service-oriented architecture
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from .core.config import settings
from .core.logging import setup_logging
from .dependencies import initialize_services, cleanup_services, get_service_container
from .routers.websocket import websocket_router
from .routers.api import api_router
from .middleware import ErrorHandlerMiddleware, RateLimitMiddleware, CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown"""

    # Startup
    logger = logging.getLogger("app.main")
    logger.info("🚀 Starting Gold Trading Dashboard...")

    try:
        # Initialize all services
        container = await initialize_services()

        # Store service container in app state
        app.state.services = container

        logger.info("✅ Application startup completed successfully!")
        logger.info("🎯 Ready to serve requests!")

        yield

    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        raise
    finally:
        # Shutdown
        logger.info("🛑 Shutting down Gold Trading Dashboard...")

        # Cleanup all services
        await cleanup_services()

        logger.info("👋 Application shutdown completed!")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""

    # Setup logging
    setup_logging()

    # Create FastAPI app with lifespan
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # Add middleware
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(
        RateLimitMiddleware, calls_per_minute=settings.RATE_LIMIT_PER_MINUTE
    )
    app.add_middleware(CORSMiddleware)

    # Mount static files
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # Setup templates
    templates = Jinja2Templates(directory="templates")

    # Include routers
    app.include_router(websocket_router, prefix="/ws", tags=["websocket"])
    app.include_router(api_router, prefix="/api", tags=["api"])

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        """Serve the main gold trading dashboard"""
        return templates.TemplateResponse("clean.html", {"request": request})

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
