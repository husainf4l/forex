"""
API routes for market data and health checks
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from ..dependencies import get_capital_service, get_websocket_manager
from ..services.capital import CapitalAPIService
from ..services.websocket import WebSocketManager
from ..models.market import MarketData
from ..core.logging import get_logger

logger = get_logger(__name__)

api_router = APIRouter()


@api_router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Gold Trading Platform",
    }


@api_router.get("/gold-live")
async def get_live_gold_data(
    capital_service: CapitalAPIService = Depends(get_capital_service),
) -> Dict[str, Any]:
    """Get live gold price data"""
    try:
        gold_data = await capital_service.get_current_price("GOLD")

        if gold_data:
            return {
                "success": True,
                "data": gold_data.dict(),
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "error": "No gold data available",
                "timestamp": datetime.now().isoformat(),
            }

    except Exception as e:
        logger.error(f"❌ Error fetching gold data: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@api_router.get("/gold-info")
async def get_gold_market_info(
    capital_service: CapitalAPIService = Depends(get_capital_service),
) -> Dict[str, Any]:
    """Get gold market information"""
    try:
        market_info = await capital_service.get_market_info("GOLD")

        if market_info:
            return {
                "success": True,
                "data": market_info.dict(),
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "error": "No market info available",
                "timestamp": datetime.now().isoformat(),
            }

    except Exception as e:
        logger.error(f"❌ Error fetching market info: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@api_router.get("/connection-status")
async def get_connection_status(
    capital_service: CapitalAPIService = Depends(get_capital_service),
    websocket_manager: WebSocketManager = Depends(get_websocket_manager),
) -> Dict[str, Any]:
    """Get connection status"""
    try:
        return {
            "capital_connected": capital_service.is_connected,
            "websocket_streaming": capital_service.is_streaming,
            "active_connections": len(websocket_manager.connections),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error getting connection status: {e}")
        return {
            "capital_connected": False,
            "websocket_streaming": False,
            "active_connections": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@api_router.get("/fetch-historical-data")
async def fetch_historical_gold_data(
    days: int = 30,
    resolution: str = "MINUTE_5",
    max_pages: int = 10,
    capital_service: CapitalAPIService = Depends(get_capital_service),
) -> Dict[str, Any]:
    """Fetch historical gold data using API pagination"""
    try:
        from ..services.data_fetcher import GoldDataFetcher

        # Create data fetcher
        fetcher = GoldDataFetcher(capital_service)
        await fetcher.initialize()

        try:
            # Calculate date range - use older dates that have data
            to_date = datetime.now() - timedelta(days=30)  # Go back 30 days
            from_date = to_date - timedelta(days=days)  # Then go back 'days' from there

            logger.info(f"🔍 Fetching {days} days of {resolution} data")
            logger.info(
                f"📅 Using date range: {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}"
            )

            # Fetch data
            data = await fetcher.fetch_historical_prices(
                resolution=resolution,
                max_pages=max_pages,
                from_date=from_date,
                to_date=to_date,
            )

            return {
                "success": True,
                "message": f"Successfully fetched {len(data)} records",
                "data_count": len(data),
                "date_range": {
                    "from": from_date.isoformat(),
                    "to": to_date.isoformat(),
                },
                "resolution": resolution,
                "sample_data": (
                    data[:5] if data else []
                ),  # Return first 5 records as sample
                "timestamp": datetime.now().isoformat(),
            }

        finally:
            await fetcher.cleanup()

    except Exception as e:
        logger.error(f"❌ Error fetching historical data: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@api_router.get("/fetch-recent-data")
async def fetch_recent_gold_data(
    hours: int = 24, capital_service: CapitalAPIService = Depends(get_capital_service)
) -> Dict[str, Any]:
    """Fetch recent gold data for specified hours"""
    try:
        from ..services.data_fetcher import GoldDataFetcher

        fetcher = GoldDataFetcher(capital_service)
        await fetcher.initialize()

        try:
            logger.info(f"🔍 Fetching recent {hours} hours of data")

            data = await fetcher.fetch_recent_data(hours=hours)

            return {
                "success": True,
                "message": f"Successfully fetched {len(data)} recent records",
                "data_count": len(data),
                "hours": hours,
                "sample_data": data[-10:] if data else [],  # Return last 10 records
                "timestamp": datetime.now().isoformat(),
            }

        finally:
            await fetcher.cleanup()

    except Exception as e:
        logger.error(f"❌ Error fetching recent data: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@api_router.get("/fetch-daily-data")
async def fetch_daily_gold_data(
    days: int = 30, capital_service: CapitalAPIService = Depends(get_capital_service)
) -> Dict[str, Any]:
    """Fetch daily gold data"""
    try:
        from ..services.data_fetcher import GoldDataFetcher

        fetcher = GoldDataFetcher(capital_service)
        await fetcher.initialize()

        try:
            logger.info(f"🔍 Fetching {days} days of daily data")

            data = await fetcher.fetch_daily_data(days=days)

            return {
                "success": True,
                "message": f"Successfully fetched {len(data)} daily records",
                "data_count": len(data),
                "days": days,
                "data": data,  # Return all daily data since it's typically smaller
                "timestamp": datetime.now().isoformat(),
            }

        finally:
            await fetcher.cleanup()

    except Exception as e:
        logger.error(f"❌ Error fetching daily data: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@api_router.post("/fetch-all-data")
async def fetch_all_available_data(
    capital_service: CapitalAPIService = Depends(get_capital_service),
) -> Dict[str, Any]:
    """Fetch all available historical data (use with caution!)"""
    try:
        from ..services.data_fetcher import GoldDataFetcher

        fetcher = GoldDataFetcher(capital_service)
        await fetcher.initialize()

        try:
            logger.warning("⚠️ Starting full historical data fetch - this may take time")

            data = await fetcher.fetch_all_available_data()

            return {
                "success": True,
                "message": f"Successfully fetched {len(data)} historical records",
                "data_count": len(data),
                "warning": "This is a large dataset - consider using pagination for client-side processing",
                "sample_data": data[:10] if data else [],
                "timestamp": datetime.now().isoformat(),
            }

        finally:
            await fetcher.cleanup()

    except Exception as e:
        logger.error(f"❌ Error fetching all data: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@api_router.get("/data-stats")
async def get_data_statistics(
    capital_service: CapitalAPIService = Depends(get_capital_service),
) -> Dict[str, Any]:
    """Get statistics about available data"""
    try:
        # This would typically query your database for statistics
        # For now, we'll return API connection status

        return {
            "success": True,
            "api_status": {
                "connected": capital_service.is_connected,
                "authenticated": capital_service.is_authenticated,
                "streaming": capital_service.is_streaming,
            },
            "available_resolutions": [
                "MINUTE",
                "MINUTE_5",
                "MINUTE_15",
                "MINUTE_30",
                "HOUR",
                "HOUR_4",
                "DAY",
            ],
            "recommended_usage": {
                "recent_data": "Use /fetch-recent-data for last 24-48 hours",
                "historical_data": "Use /fetch-historical-data with pagination",
                "daily_summary": "Use /fetch-daily-data for daily OHLC data",
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Error getting data stats: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
