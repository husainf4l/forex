"""
Service factory and dependency injection for the Gold Trading Dashboard
"""

import asyncio
from typing import Optional
from functools import lru_cache

from .services.capital import CapitalAPIService
from .services.websocket import WebSocketManager
from .services.database import DatabaseService
from .core.config import settings
from .core.logging import get_logger

logger = get_logger(__name__)


class ServiceContainer:
    """Service container for dependency injection"""

    def __init__(self):
        self._capital_service: Optional[CapitalAPIService] = None
        self._websocket_manager: Optional[WebSocketManager] = None
        self._database_service: Optional[DatabaseService] = None
        self._initialized: bool = False

    async def initialize(self) -> None:
        """Initialize all services"""
        if self._initialized:
            return

        logger.info("🚀 Initializing service container...")

        # Initialize database service first
        self._database_service = DatabaseService()
        await self._database_service.initialize()

        # Initialize Capital service
        self._capital_service = CapitalAPIService()
        await self._capital_service.initialize()

        # Initialize WebSocket manager
        self._websocket_manager = WebSocketManager()
        await self._websocket_manager.initialize()

        # Start streaming with price callback
        await self._capital_service.start_streaming(
            self._websocket_manager.broadcast_price_update
        )

        self._initialized = True
        logger.info("✅ Service container initialized successfully!")

    async def cleanup(self) -> None:
        """Cleanup all services"""
        if not self._initialized:
            return

        logger.info("🧹 Cleaning up service container...")

        if self._database_service:
            await self._database_service.cleanup()
            self._database_service = None

        if self._capital_service:
            await self._capital_service.cleanup()
            self._capital_service = None

        if self._websocket_manager:
            await self._websocket_manager.cleanup()
            self._websocket_manager = None

        self._initialized = False
        logger.info("✅ Service container cleanup completed!")

    @property
    def database_service(self) -> DatabaseService:
        """Get database service instance"""
        if not self._database_service:
            raise RuntimeError("Database service not initialized")
        return self._database_service

    @property
    def capital_service(self) -> CapitalAPIService:
        """Get Capital service instance"""
        if not self._capital_service:
            raise RuntimeError("Capital service not initialized")
        return self._capital_service

    @property
    def websocket_manager(self) -> WebSocketManager:
        """Get WebSocket manager instance"""
        if not self._websocket_manager:
            raise RuntimeError("WebSocket manager not initialized")
        return self._websocket_manager

    @property
    def is_initialized(self) -> bool:
        """Check if services are initialized"""
        return self._initialized


# Global service container instance
_service_container: Optional[ServiceContainer] = None


def get_service_container() -> ServiceContainer:
    """Get or create the global service container"""
    global _service_container
    if _service_container is None:
        _service_container = ServiceContainer()
    return _service_container


async def initialize_services() -> ServiceContainer:
    """Initialize all services"""
    container = get_service_container()
    await container.initialize()
    return container


async def cleanup_services() -> None:
    """Cleanup all services"""
    global _service_container
    if _service_container:
        await _service_container.cleanup()
        _service_container = None


@lru_cache()
def get_database_service() -> DatabaseService:
    """Dependency injection for Database service"""
    return get_service_container().database_service


@lru_cache()
def get_capital_service() -> CapitalAPIService:
    """Dependency injection for Capital service"""
    return get_service_container().capital_service


@lru_cache()
def get_websocket_manager() -> WebSocketManager:
    """Dependency injection for WebSocket manager"""
    return get_service_container().websocket_manager
