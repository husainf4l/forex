# Capital.com API Integration
import requests
import json
from typing import Dict, Optional, Callable
from datetime import datetime
import os
from dotenv import load_dotenv
import asyncio
import websockets
import threading
import time
import uuid

load_dotenv()


class CapitalAPI:
    def __init__(self, demo=False):
        # Load credentials from .env file
        self.api_key = os.getenv("CAPITAL_API_KEY")
        self.email = os.getenv("CAPITAL_EMAIL")
        self.password = os.getenv("CAPITAL_PASSWORD")

        # Debug credential loading
        print(f"🔑 API Key loaded: {'✅' if self.api_key else '❌'}")
        print(f"📧 Email loaded: {'✅' if self.email else '❌'}")
        print(f"🔑 Password loaded: {'✅' if self.password else '❌'}")

        # API URLs
        self.base_url = (
            "https://demo-api-capital.backend-capital.com"
            if demo
            else "https://api-capital.backend-capital.com"
        )
        self.websocket_url = "wss://api-streaming-capital.backend-capital.com"

        # Authentication tokens
        self.session_token = None
        self.security_token = None

        # Account info
        self.account_id = None
        self.client_id = None
        self.streaming_host = None

        # Base headers
        self.headers = {
            "X-CAP-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Version": "1",
        }

        # WebSocket related attributes
        self.websocket = None
        self.websocket_connected = False
        self.price_callbacks = []
        self.websocket_thread = None
        self.should_stop_websocket = False
        self.correlation_id_counter = 0
        self.last_ping_time = 0

        # Gold market identifier - try common variations
        self.gold_epics = ["GOLD", "XAU/USD", "XAUUSD", "GOLD_USD", "XAU_USD"]
        self.subscribed_epic = None

        # Latest price data
        self.latest_price_data = None

    def login(self) -> bool:
        """Login to Capital.com API using email and API password"""
        print("🔄 Attempting Capital.com API authentication...")

        # Validate credentials
        if not all([self.api_key, self.email, self.password]):
            print("❌ Missing credentials. Please check your .env file.")
            return False

        # API endpoint
        url = f"{self.base_url}/api/v1/session"

        # Headers
        headers = {"X-CAP-API-KEY": self.api_key, "Content-Type": "application/json"}

        # Request payload
        payload = {"identifier": self.email, "password": self.password}

        print(f"🌐 Making request to: {url}")
        print(f"📧 Using email: {self.email}")
        print(f"🔑 Using API key: {self.api_key[:10]}...")

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            print(f"✅ Response Status: {response.status_code}")

            if response.status_code == 200:
                # Extract tokens from headers
                self.session_token = response.headers.get("CST")
                self.security_token = response.headers.get("X-SECURITY-TOKEN")

                print(f"🎫 CST Token: {self.session_token}")
                print(f"🔐 Security Token: {self.security_token}")

                # Update headers for future requests
                self.headers.update(
                    {"CST": self.session_token, "X-SECURITY-TOKEN": self.security_token}
                )

                # Store account info
                response_data = response.json()
                self.account_id = response_data.get("currentAccountId")
                self.client_id = response_data.get("clientId")
                self.streaming_host = response_data.get("streamingHost")

                print(f"📊 Account ID: {self.account_id}")
                print(f"👤 Client ID: {self.client_id}")
                print(f"🌐 Streaming Host: {self.streaming_host}")

                return True
            else:
                print(f"❌ Login failed with status {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"📦 Error response: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"📦 Error response (text): {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return False

    def is_authenticated(self) -> bool:
        """Check if the API is authenticated"""
        return self.session_token is not None and self.security_token is not None

    def logout(self) -> bool:
        """Logout from Capital.com API"""
        if not self.is_authenticated():
            print("❌ Not authenticated, cannot logout")
            return False

        url = f"{self.base_url}/api/v1/session"

        try:
            response = requests.delete(url, headers=self.headers, timeout=30)

            if response.status_code == 204:
                print("✅ Logout successful")
                self.session_token = None
                self.security_token = None
                self.headers = {
                    "X-CAP-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                    "Version": "1",
                }
                return True
            else:
                print(f"❌ Logout failed with status {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ Logout request failed: {e}")
            return False

    def get_gold_price(self) -> Optional[Dict]:
        """Get live GOLD price from Capital.com - prefer streaming data if available"""

        # If we have recent streaming data, use it
        if self.latest_price_data and self.websocket_connected:
            streaming_data = self.latest_price_data
            return {
                "symbol": "GOLD",
                "bid": streaming_data.get("bid"),
                "ask": streaming_data.get("ask"),
                "mid": streaming_data.get("mid"),
                "spread": streaming_data.get("spread"),
                "timestamp": streaming_data.get("timestamp"),
                "source": "websocket_stream",
            }

        # Fallback to REST API
        if not self.session_token:
            if not self.login():
                return None

        # Try different possible endpoints for gold data
        endpoints = [
            f"{self.base_url}/api/v1/prices/GOLD",
            f"{self.base_url}/api/v1/markets/GOLD/prices",
            f"{self.base_url}/api/v1/prices?epics=GOLD",
        ]

        for url in endpoints:
            try:
                print(f"🔍 Trying REST endpoint: {url}")
                response = requests.get(url, headers=self.headers, timeout=10)
                print(f"📊 Response status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    print(f"📦 Response data: {data}")

                    # Handle Capital.com's price response format
                    if "prices" in data and len(data["prices"]) > 0:
                        # Get the latest price data (last item in the array)
                        latest_price = data["prices"][-1]

                        # Extract close prices (current prices)
                        close_price = latest_price.get("closePrice", {})
                        high_price = latest_price.get("highPrice", {})
                        low_price = latest_price.get("lowPrice", {})
                        open_price = latest_price.get("openPrice", {})

                        bid = close_price.get("bid")
                        ask = close_price.get("ask")
                        high = high_price.get("bid")  # Use bid for high
                        low = low_price.get("bid")  # Use bid for low
                        open_val = open_price.get("bid")  # Use bid for open

                        # Calculate mid price and changes
                        mid = (bid + ask) / 2 if bid and ask else None

                        # Calculate change from open to current
                        change = (bid - open_val) if bid and open_val else None
                        change_pct = (
                            ((bid - open_val) / open_val * 100)
                            if bid and open_val
                            else None
                        )

                        return {
                            "symbol": "GOLD",
                            "bid": float(bid) if bid else None,
                            "ask": float(ask) if ask else None,
                            "mid": float(mid) if mid else None,
                            "high": float(high) if high else None,
                            "low": float(low) if low else None,
                            "change": float(change) if change else None,
                            "changePercent": float(change_pct) if change_pct else None,
                            "open": float(open_val) if open_val else None,
                            "timestamp": latest_price.get(
                                "snapshotTime", datetime.now().isoformat()
                            ),
                            "market_status": "OPEN",
                            "source": "rest_api",
                        }

                    # Handle other response formats
                    elif isinstance(data, dict):
                        # Direct response format
                        price_data = data
                    elif isinstance(data, list) and len(data) > 0:
                        # Array response format
                        price_data = data[0]
                    else:
                        continue

                    # Extract price information with multiple possible field names (fallback)
                    bid = (
                        price_data.get("bid")
                        or price_data.get("bidPrice")
                        or price_data.get("buy")
                    )
                    ask = (
                        price_data.get("offer")
                        or price_data.get("ask")
                        or price_data.get("askPrice")
                        or price_data.get("sell")
                    )
                    high = price_data.get("high") or price_data.get("dayHigh")
                    low = price_data.get("low") or price_data.get("dayLow")
                    change = (
                        price_data.get("netChange")
                        or price_data.get("change")
                        or price_data.get("priceChange")
                    )
                    change_pct = (
                        price_data.get("pctChange")
                        or price_data.get("changePercent")
                        or price_data.get("percentChange")
                    )
                    open_price = price_data.get("open") or price_data.get("openPrice")

                    # Calculate mid price if not available
                    mid = None
                    if bid and ask:
                        mid = (float(bid) + float(ask)) / 2

                    if bid or ask:  # If we have at least one price
                        return {
                            "symbol": "GOLD",
                            "bid": float(bid) if bid else None,
                            "ask": float(ask) if ask else None,
                            "mid": mid,
                            "high": float(high) if high else None,
                            "low": float(low) if low else None,
                            "change": float(change) if change else None,
                            "changePercent": float(change_pct) if change_pct else None,
                            "open": float(open_price) if open_price else None,
                            "timestamp": datetime.now().isoformat(),
                            "market_status": price_data.get("marketStatus", "UNKNOWN"),
                            "source": "rest_api",
                        }
                else:
                    print(
                        f"❌ Failed to get gold price: {response.status_code} - {response.text}"
                    )

            except Exception as e:
                print(f"❌ Error getting gold price from {url}: {e}")
                continue

        print("❌ All endpoints failed, no gold price data available")
        return None

    def get_market_info(self) -> Optional[Dict]:
        """Get GOLD market information"""
        if not self.session_token:
            if not self.login():
                return None

        url = f"{self.base_url}/api/v1/markets/GOLD"

        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error getting market info: {e}")
            return None

    def test_connection(self) -> Dict:
        """Test the Capital.com API connection and endpoints"""
        results = {
            "api_key_present": bool(self.api_key),
            "custom_key_present": bool(self.custom_key),
            "base_url": self.base_url,
            "login_test": False,
            "endpoints_test": {},
        }

        # Test login
        print("🧪 Testing Capital.com API connection...")
        results["login_test"] = self.login()

        if results["login_test"]:
            # Test endpoints if login successful
            endpoints = [
                ("/api/v1/markets", "markets"),
                ("/api/v1/prices", "prices"),
                ("/api/v1/markets/GOLD", "gold_market"),
                ("/api/v1/prices/GOLD", "gold_price"),
            ]

            for endpoint, name in endpoints:
                try:
                    url = f"{self.base_url}{endpoint}"
                    response = requests.get(url, headers=self.headers, timeout=10)
                    results["endpoints_test"][name] = {
                        "status_code": response.status_code,
                        "success": response.status_code == 200,
                        "response_size": len(response.text) if response.text else 0,
                    }
                    print(f"✅ {name}: {response.status_code}")
                except Exception as e:
                    results["endpoints_test"][name] = {
                        "status_code": 0,
                        "success": False,
                        "error": str(e),
                    }
                    print(f"❌ {name}: {str(e)}")

        return results

    def get_available_markets(self) -> Optional[Dict]:
        """Get list of available markets from Capital.com"""
        if not self.session_token:
            if not self.login():
                return None

        url = f"{self.base_url}/api/v1/markets"

        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get markets: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error getting markets: {e}")
            return None

    # WebSocket functionality for real-time data

    def add_price_callback(self, callback: Callable):
        """Add a callback function to be called when new price data is received"""
        self.price_callbacks.append(callback)

    def remove_price_callback(self, callback: Callable):
        """Remove a callback function"""
        if callback in self.price_callbacks:
            self.price_callbacks.remove(callback)

    def _notify_price_callbacks(self, price_data: dict):
        """Notify all registered callbacks with new price data"""
        for callback in self.price_callbacks:
            try:
                callback(price_data)
            except Exception as e:
                print(f"Error in price callback: {e}")

    def _get_next_correlation_id(self) -> str:
        """Get the next correlation ID for WebSocket messages"""
        self.correlation_id_counter += 1
        return str(self.correlation_id_counter)

    async def _websocket_handler(self):
        """Handle real-time data stream using Capital.com WebSocket API"""
        print("🔗 Starting WebSocket connection to Capital.com streaming API")

        if not self.session_token or not self.security_token:
            print("❌ Authentication tokens not available")
            return

        try:
            # Connect to Capital.com WebSocket endpoint
            async with websockets.connect(f"{self.websocket_url}/connect") as websocket:
                self.websocket = websocket
                self.websocket_connected = True
                print("✅ WebSocket connected successfully")

                # Subscribe to GOLD market data
                await self._subscribe_to_market_data(websocket)

                # Start ping task to keep connection alive
                ping_task = asyncio.create_task(self._ping_service(websocket))

                # Listen for messages
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await self._handle_websocket_message(data)
                    except json.JSONDecodeError as e:
                        print(f"❌ Failed to parse WebSocket message: {e}")
                    except Exception as e:
                        print(f"❌ Error handling WebSocket message: {e}")

        except websockets.exceptions.ConnectionClosed:
            print("🔌 WebSocket connection closed")
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
        finally:
            self.websocket_connected = False
            self.websocket = None
            print("🔌 WebSocket handler finished")

    async def _subscribe_to_market_data(self, websocket):
        """Subscribe to GOLD market data"""
        print("📊 Subscribing to GOLD market data...")

        # Try different possible GOLD epics
        for epic in self.gold_epics:
            subscription_message = {
                "destination": "marketData.subscribe",
                "correlationId": self._get_next_correlation_id(),
                "cst": self.session_token,
                "securityToken": self.security_token,
                "payload": {"epics": [epic]},
            }

            try:
                await websocket.send(json.dumps(subscription_message))
                print(f"📡 Subscription request sent for {epic}")

                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                response_data = json.loads(response)

                if (
                    response_data.get("status") == "OK"
                    and response_data.get("destination") == "marketData.subscribe"
                ):
                    subscriptions = response_data.get("payload", {}).get(
                        "subscriptions", {}
                    )
                    if epic in subscriptions and subscriptions[epic] == "PROCESSED":
                        print(f"✅ Successfully subscribed to {epic}")
                        self.subscribed_epic = epic
                        return
                    else:
                        print(f"❌ Failed to subscribe to {epic}: {subscriptions}")
                else:
                    print(f"❌ Subscription response error for {epic}: {response_data}")

            except Exception as e:
                print(f"❌ Error subscribing to {epic}: {e}")
                continue

        print("❌ Failed to subscribe to any GOLD epic")

    async def _ping_service(self, websocket):
        """Send periodic pings to keep connection alive"""
        try:
            while self.websocket_connected and not self.should_stop_websocket:
                await asyncio.sleep(300)  # Ping every 5 minutes (10 min max)

                if self.websocket_connected:
                    ping_message = {
                        "destination": "ping",
                        "correlationId": self._get_next_correlation_id(),
                        "cst": self.session_token,
                        "securityToken": self.security_token,
                    }

                    try:
                        await websocket.send(json.dumps(ping_message))
                        print("🏓 Ping sent to keep connection alive")
                    except Exception as e:
                        print(f"❌ Error sending ping: {e}")
                        break

        except Exception as e:
            print(f"❌ Ping service error: {e}")

    async def _handle_websocket_message(self, data: dict):
        """Handle incoming WebSocket messages"""
        destination = data.get("destination")
        status = data.get("status")

        if destination == "marketData.subscribe":
            # Handle subscription response
            if status == "OK":
                subscriptions = data.get("payload", {}).get("subscriptions", {})
                print(f"📊 Subscription status: {subscriptions}")
            else:
                print(f"❌ Subscription failed: {data}")

        elif destination == "quote":
            # Handle price updates
            payload = data.get("payload", {})
            epic = payload.get("epic")

            if epic == self.subscribed_epic:
                # Process price data
                price_data = {
                    "epic": epic,
                    "product": payload.get("product"),
                    "bid": payload.get("bid"),
                    "ask": payload.get("ofr"),  # Capital.com uses "ofr" for ask
                    "bidQty": payload.get("bidQty"),
                    "askQty": payload.get("ofrQty"),
                    "timestamp": payload.get("timestamp"),
                    "raw_timestamp": payload.get("timestamp"),
                }

                # Calculate additional fields
                if price_data["bid"] and price_data["ask"]:
                    price_data["mid"] = (price_data["bid"] + price_data["ask"]) / 2
                    price_data["spread"] = price_data["ask"] - price_data["bid"]

                # Convert timestamp to ISO format
                if price_data["timestamp"]:
                    try:
                        price_data["timestamp"] = datetime.fromtimestamp(
                            price_data["timestamp"] / 1000
                        ).isoformat()
                    except:
                        price_data["timestamp"] = datetime.now().isoformat()
                else:
                    price_data["timestamp"] = datetime.now().isoformat()

                print(
                    f"💰 Real-time Gold Price: Bid=${price_data['bid']}, Ask=${price_data['ask']}, Mid=${price_data.get('mid')}"
                )

                # Store latest price data
                self.latest_price_data = price_data

                # Notify callbacks
                self._notify_price_callbacks(price_data)

        elif destination == "ping":
            # Handle ping response
            if status == "OK":
                print("🏓 Ping response received")
            else:
                print(f"❌ Ping failed: {data}")

        elif destination == "ohlc.event":
            # Handle OHLC data (candlestick updates)
            payload = data.get("payload", {})
            print(f"📊 OHLC update: {payload}")

        else:
            print(f"🔍 Unknown WebSocket message: {data}")

    def start_websocket_stream(self):
        """Start WebSocket streaming in a separate thread"""
        if self.websocket_connected:
            print("⚠️ WebSocket already connected")
            return

        if not self.is_authenticated():
            print("❌ Not authenticated. Please login first.")
            return

        self.should_stop_websocket = False

        def run_websocket():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._websocket_handler())
            finally:
                loop.close()

        self.websocket_thread = threading.Thread(target=run_websocket, daemon=True)
        self.websocket_thread.start()
        print("🚀 WebSocket streaming started")

    def stop_websocket_stream(self):
        """Stop WebSocket streaming"""
        if not self.websocket_connected:
            print("⚠️ WebSocket not connected")
            return

        self.should_stop_websocket = True

        if self.websocket_thread and self.websocket_thread.is_alive():
            self.websocket_thread.join(timeout=5)

        self.websocket_connected = False
        print("🛑 WebSocket streaming stopped")

    def is_websocket_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.websocket_connected

    def get_latest_streaming_price(self) -> Optional[Dict]:
        """Get the latest price data from WebSocket stream"""
        return self.latest_price_data
