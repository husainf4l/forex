"""
Professional Capital.com API Service with async best practices
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List
import aiohttp
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from ..core.config import settings
from ..core.logging import get_logger
from ..models.market import PriceTick, MarketData, MarketStatus

logger = get_logger(__name__)


class CapitalAPIError(Exception):
    """Custom exception for Capital API errors"""

    pass


class CapitalAPIService:
    """
    Professional async Capital.com API service
    """

    def __init__(self):
        # API Configuration
        self.api_key = settings.CAPITAL_API_KEY
        self.email = settings.CAPITAL_EMAIL
        self.password = settings.CAPITAL_PASSWORD
        self.demo = settings.CAPITAL_DEMO

        # API URLs
        if settings.CAPITAL_BASE_URL:
            self.base_url = settings.CAPITAL_BASE_URL
        elif self.demo:
            self.base_url = "https://demo-api-capital.backend-capital.com"
        else:
            self.base_url = "https://api-capital.backend-capital.com"

        if settings.CAPITAL_WEBSOCKET_URL:
            self.websocket_url = settings.CAPITAL_WEBSOCKET_URL
        else:
            self.websocket_url = "wss://api-streaming-capital.backend-capital.com"

        # Authentication state
        self.session_token: Optional[str] = None
        self.security_token: Optional[str] = None
        self.account_id: Optional[str] = None
        self.client_id: Optional[str] = None

        # Connection state
        self.is_authenticated = False
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self._is_streaming = False

        # Callbacks
        self.price_callback: Optional[Callable[[PriceTick], None]] = None

        # Session
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()

    async def initialize(self) -> None:
        """Initialize the service"""
        logger.info("🚀 Initializing Capital.com API service")

        # Create aiohttp session
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)

        # Authenticate
        await self.authenticate()

        logger.info("✅ Capital.com API service initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup resources"""
        logger.info("🧹 Cleaning up Capital.com API service")

        # Stop streaming
        if self.is_streaming:
            await self.stop_streaming()

        # Close websocket
        if self.websocket:
            await self.websocket.close()

        # Close HTTP session
        if self.session:
            await self.session.close()

        logger.info("✅ Capital.com API service cleanup completed")

    async def authenticate(self) -> bool:
        """Authenticate with Capital.com API"""
        if not all([self.api_key, self.email, self.password]):
            raise CapitalAPIError("Missing required credentials")

        headers = {
            "X-CAP-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Version": "1",
        }

        payload = {"identifier": self.email, "password": self.password}

        try:
            logger.info("🔐 Authenticating with Capital.com API")

            async with self.session.post(
                f"{self.base_url}/api/v1/session", headers=headers, json=payload
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    raise CapitalAPIError(
                        f"Authentication failed: {response.status} - {error_text}"
                    )

                # Extract tokens from headers
                self.session_token = response.headers.get("CST")
                self.security_token = response.headers.get("X-SECURITY-TOKEN")

                if not self.session_token or not self.security_token:
                    raise CapitalAPIError("Missing authentication tokens in response")

                # Get account info from response body
                data = await response.json()
                self.account_id = str(data.get("accountId"))
                self.client_id = str(data.get("clientId"))

                self.is_authenticated = True

                logger.info("✅ Authentication successful")
                logger.info(f"📊 Account ID: {self.account_id}")
                logger.info(f"👤 Client ID: {self.client_id}")

                return True

        except aiohttp.ClientError as e:
            logger.error(f"❌ Network error during authentication: {e}")
            raise CapitalAPIError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error during authentication: {e}")
            raise CapitalAPIError(f"Authentication error: {e}")

    async def get_market_data(
        self, epic: str = "CS.D.CFEGOLD.CFE.IP"
    ) -> Optional[MarketData]:
        """Get current market data for gold"""
        if not self.is_authenticated:
            await self.authenticate()

        headers = {
            "X-CAP-API-KEY": self.api_key,
            "CST": self.session_token,
            "X-SECURITY-TOKEN": self.security_token,
            "Version": "1",
        }

        try:
            async with self.session.get(
                f"{self.base_url}/api/v1/markets/{epic}", headers=headers
            ) as response:

                if response.status != 200:
                    logger.error(f"❌ Failed to get market data: {response.status}")
                    return None

                data = await response.json()
                market_info = data.get("market", {})
                snapshot = data.get("snapshot", {})

                return MarketData(
                    symbol="XAU/USD",
                    current_price=float(snapshot.get("offer", 0)),
                    bid=float(snapshot.get("bid", 0)),
                    ask=float(snapshot.get("offer", 0)),
                    spread=float(snapshot.get("offer", 0))
                    - float(snapshot.get("bid", 0)),
                    high_24h=float(snapshot.get("high", 0)),
                    low_24h=float(snapshot.get("low", 0)),
                    change_24h=float(snapshot.get("netChange", 0)),
                    change_percent_24h=float(snapshot.get("percentageChange", 0)),
                    last_update=datetime.now(),
                    market_status=(
                        MarketStatus.OPEN
                        if market_info.get("marketStatus") == "TRADEABLE"
                        else MarketStatus.CLOSED
                    ),
                )

        except Exception as e:
            logger.error(f"❌ Error getting market data: {e}")
            return None

    async def get_current_price(self, symbol: str = "GOLD") -> Optional[PriceTick]:
        """Get current price for a symbol"""
        market_data = await self.get_market_data(symbol)
        if market_data:
            return PriceTick(
                timestamp=market_data.last_update,
                bid=market_data.bid,
                ask=market_data.ask,
                mid=market_data.current_price,
                volume=None,
            )
        return None

    async def get_market_info(self, symbol: str = "GOLD") -> Optional[MarketData]:
        """Get market information for a symbol"""
        return await self.get_market_data(symbol)

    def add_price_callback(self, callback: Callable[[PriceTick], None]) -> None:
        """Add a price callback function"""
        self.price_callback = callback

    @property
    def is_connected(self) -> bool:
        """Check if the service is connected"""
        return self.is_authenticated

    @property
    def is_streaming(self) -> bool:
        """Check if streaming is active"""
        return self._is_streaming

    @is_streaming.setter
    def is_streaming(self, value: bool) -> None:
        """Set streaming status"""
        self._is_streaming = value

    async def start_streaming(
        self, price_callback: Callable[[PriceTick], None]
    ) -> None:
        """Start WebSocket streaming"""
        if not self.is_authenticated:
            await self.authenticate()

        self.price_callback = price_callback

        # Start streaming in background task
        asyncio.create_task(self._streaming_loop())

    async def _streaming_loop(self) -> None:
        """Main streaming loop with reconnection logic"""
        max_retries = 5
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"🔗 Starting WebSocket connection (attempt {attempt + 1}/{max_retries})"
                )

                headers = {
                    "CST": self.session_token,
                    "X-SECURITY-TOKEN": self.security_token,
                }

                async with websockets.connect(
                    f"{self.websocket_url}/connect",
                    additional_headers=headers,
                    ping_interval=settings.WEBSOCKET_PING_INTERVAL,
                    ping_timeout=settings.WEBSOCKET_PING_TIMEOUT,
                ) as websocket:

                    self.websocket = websocket
                    self._is_streaming = True

                    # Subscribe to gold prices
                    await self._subscribe_to_gold()

                    logger.info("✅ WebSocket streaming started successfully")

                    # Listen for messages
                    async for message in websocket:
                        await self._handle_websocket_message(message)

            except ConnectionClosed:
                logger.warning("🔌 WebSocket connection closed")
                self._is_streaming = False

            except WebSocketException as e:
                logger.error(f"❌ WebSocket error: {e}")
                self._is_streaming = False

            except Exception as e:
                logger.error(f"❌ Unexpected streaming error: {e}")
                self._is_streaming = False

            # Exponential backoff
            if attempt < max_retries - 1:
                logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)
            else:
                logger.error("❌ Max retry attempts reached. Streaming stopped.")

    async def _subscribe_to_gold(self) -> None:
        """Subscribe to gold price updates"""
        # Try different possible GOLD epics
        gold_epics = ["GOLD", "CS.D.CFEGOLD.CFE.IP", "XAU/USD", "XAUUSD"]

        for epic in gold_epics:
            subscription = {
                "destination": "marketData.subscribe",
                "correlationId": str(uuid.uuid4()),
                "cst": self.session_token,
                "securityToken": self.security_token,
                "payload": {"epics": [epic]},
            }

            try:
                await self.websocket.send(json.dumps(subscription))
                logger.info(f"📡 Subscription request sent for {epic}")

                # Wait for response with timeout
                response = await asyncio.wait_for(self.websocket.recv(), timeout=5)
                response_data = json.loads(response)

                if (
                    response_data.get("status") == "OK"
                    and response_data.get("destination") == "marketData.subscribe"
                ):
                    subscriptions = response_data.get("payload", {}).get("subscriptions", {})
                    if epic in subscriptions and subscriptions[epic] == "PROCESSED":
                        logger.info(f"✅ Successfully subscribed to {epic}")
                        return
                    else:
                        logger.warning(f"❌ Failed to subscribe to {epic}: {subscriptions}")
                else:
                    logger.warning(f"❌ Subscription response error for {epic}: {response_data}")

            except Exception as e:
                logger.error(f"❌ Error subscribing to {epic}: {e}")
                continue

        logger.error("❌ Failed to subscribe to any GOLD epic")

    async def _handle_websocket_message(self, message: str) -> None:
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            destination = data.get("destination")
            status = data.get("status")

            if destination == "marketData.subscribe":
                # Handle subscription response
                if status == "OK":
                    subscriptions = data.get("payload", {}).get("subscriptions", {})
                    logger.info(f"📊 Subscription status: {subscriptions}")
                else:
                    logger.error(f"❌ Subscription failed: {data}")

            elif destination == "quote":
                # Handle price updates
                payload = data.get("payload", {})
                epic = payload.get("epic")

                # Process price data
                bid = payload.get("bid")
                ask = payload.get("ofr")  # Capital.com uses "ofr" for ask

                if bid and ask:
                    # Create price tick
                    price_tick = PriceTick(
                        timestamp=datetime.now(),
                        bid=float(bid),
                        ask=float(ask),
                        mid=(float(bid) + float(ask)) / 2,
                        volume=None,
                    )

                    logger.info(
                        f"💰 Real-time Gold Price: Bid=${bid}, Ask=${ask}, Mid=${price_tick.mid}"
                    )

                    # Call callback
                    if self.price_callback:
                        await self._safe_callback(price_tick)

            elif destination == "ping":
                # Handle ping response
                if status == "OK":
                    logger.info("🏓 Ping response received")
                else:
                    logger.warning(f"❌ Ping failed: {data}")

            else:
                logger.debug(f"🔍 Unknown WebSocket message: {data}")

        except json.JSONDecodeError:
            logger.warning(f"⚠️ Invalid JSON message: {message}")
        except Exception as e:
            logger.error(f"❌ Error processing WebSocket message: {e}")

    async def _safe_callback(self, price_tick: PriceTick) -> None:
        """Safely execute price callback"""
        try:
            if asyncio.iscoroutinefunction(self.price_callback):
                await self.price_callback(price_tick)
            else:
                self.price_callback(price_tick)
        except Exception as e:
            logger.error(f"❌ Error in price callback: {e}")

    async def stop_streaming(self) -> None:
        """Stop WebSocket streaming"""
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()

        self._is_streaming = False
        logger.info("🛑 WebSocket streaming stopped")
