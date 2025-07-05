"""
Professional WebSocket connection manager with async best practices
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from fastapi import WebSocket, WebSocketDisconnect

from ..core.config import settings
from ..core.logging import get_logger
from ..models.market import ConnectionInfo, WebSocketMessage, PriceTick

logger = get_logger(__name__)


class WebSocketManager:
    """
    Professional WebSocket connection manager
    """

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.connection_info: Dict[str, ConnectionInfo] = {}
        self._price_history: List[Dict[str, Any]] = []
        self._cleanup_task: Optional[asyncio.Task] = None
        self._max_connections = settings.WEBSOCKET_MAX_CONNECTIONS
        self._max_price_history = settings.MAX_PRICE_HISTORY

    async def initialize(self) -> None:
        """Initialize the WebSocket manager"""
        logger.info("🚀 Initializing WebSocket manager")

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("✅ WebSocket manager initialized")

    async def cleanup(self) -> None:
        """Cleanup WebSocket manager"""
        logger.info("🧹 Cleaning up WebSocket manager")

        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()

        # Close all connections
        for connection_id in list(self.connections.keys()):
            await self.disconnect(connection_id)

        logger.info("✅ WebSocket manager cleanup completed")

    async def connect(self, websocket: WebSocket) -> str:
        """Accept new WebSocket connection"""
        # Check connection limits
        if len(self.connections) >= self._max_connections:
            await websocket.close(code=1008, reason="Maximum connections exceeded")
            raise Exception(f"Maximum connections ({self._max_connections}) exceeded")

        await websocket.accept()

        connection_id = str(uuid.uuid4())
        self.connections[connection_id] = websocket
        self.connection_info[connection_id] = ConnectionInfo(
            id=connection_id, connected_at=datetime.now()
        )

        logger.info(f"🔗 New WebSocket connection: {connection_id}")
        logger.info(
            f"📊 Total connections: {len(self.connections)}/{self._max_connections}"
        )

        # Send welcome message
        await self.send_message(
            connection_id,
            WebSocketMessage(
                type="connection_established",
                data={"connection_id": connection_id},
                timestamp=datetime.now(),
            ),
        )

        # Send recent price history
        await self._send_price_history(connection_id)

        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """Disconnect WebSocket connection"""
        if connection_id in self.connections:
            websocket = self.connections[connection_id]

            try:
                await websocket.close()
            except Exception as e:
                logger.warning(f"⚠️ Error closing WebSocket {connection_id}: {e}")

            del self.connections[connection_id]

        if connection_id in self.connection_info:
            del self.connection_info[connection_id]

        logger.info(f"🔌 WebSocket disconnected: {connection_id}")
        logger.info(f"📊 Total connections: {len(self.connections)}")

    async def send_message(self, connection_id: str, message: WebSocketMessage) -> bool:
        """Send message to specific connection"""
        if connection_id not in self.connections:
            return False

        websocket = self.connections[connection_id]

        try:
            message_dict = message.dict()
            if message_dict.get("timestamp"):
                message_dict["timestamp"] = message_dict["timestamp"].isoformat()

            await websocket.send_text(json.dumps(message_dict))
            return True

        except WebSocketDisconnect:
            logger.info(f"🔌 Client {connection_id} disconnected during send")
            await self.disconnect(connection_id)
            return False

        except Exception as e:
            logger.error(f"❌ Error sending message to {connection_id}: {e}")
            await self.disconnect(connection_id)
            return False

    async def broadcast(self, message: WebSocketMessage) -> int:
        """Broadcast message to all connections"""
        if not self.connections:
            return 0

        successful_sends = 0
        failed_connections = []

        for connection_id in self.connections:
            success = await self.send_message(connection_id, message)
            if success:
                successful_sends += 1
            else:
                failed_connections.append(connection_id)

        # Clean up failed connections
        for connection_id in failed_connections:
            await self.disconnect(connection_id)

        return successful_sends

    async def broadcast_price_update(self, price_tick: PriceTick) -> None:
        """Broadcast price update to all connections"""
        # Store in price history
        price_data = {
            "timestamp": price_tick.timestamp.isoformat(),
            "bid": price_tick.bid,
            "ask": price_tick.ask,
            "mid": price_tick.mid,
            "spread": (
                (price_tick.ask - price_tick.bid)
                if price_tick.bid and price_tick.ask
                else None
            ),
            "volume": price_tick.volume,
        }

        self._price_history.append(price_data)

        # Keep only recent history
        if len(self._price_history) > self._max_price_history:
            self._price_history = self._price_history[-self._max_price_history :]

        # Broadcast to all connections
        message = WebSocketMessage(
            type="gold_price_update", data=price_data, timestamp=price_tick.timestamp
        )

        sent_count = await self.broadcast(message)

        if sent_count > 0:
            logger.debug(f"📡 Price update broadcasted to {sent_count} connections")

    async def handle_client_message(self, connection_id: str, message: str) -> None:
        """Handle message from client"""
        try:
            data = json.loads(message)
            message_type = data.get("type")

            if message_type == "ping":
                await self._handle_ping(connection_id)
            elif message_type == "get_current_price":
                await self._handle_get_current_price(connection_id)
            elif message_type == "get_price_history":
                await self._handle_get_price_history(
                    connection_id, data.get("data", {})
                )
            elif message_type == "start_streaming":
                await self._handle_start_streaming(connection_id)
            elif message_type == "stop_streaming":
                await self._handle_stop_streaming(connection_id)
            else:
                logger.warning(
                    f"⚠️ Unknown message type from {connection_id}: {message_type}"
                )

        except json.JSONDecodeError:
            logger.warning(f"⚠️ Invalid JSON from {connection_id}: {message}")
        except Exception as e:
            logger.error(f"❌ Error handling message from {connection_id}: {e}")

    async def _handle_ping(self, connection_id: str) -> None:
        """Handle ping message"""
        if connection_id in self.connection_info:
            self.connection_info[connection_id].last_ping = datetime.now()

        await self.send_message(
            connection_id, WebSocketMessage(type="pong", timestamp=datetime.now())
        )

    async def _handle_get_current_price(self, connection_id: str) -> None:
        """Handle request for current price"""
        if self._price_history:
            latest_price = self._price_history[-1]
            await self.send_message(
                connection_id,
                WebSocketMessage(
                    type="current_price", data=latest_price, timestamp=datetime.now()
                ),
            )
        else:
            await self.send_message(
                connection_id,
                WebSocketMessage(
                    type="current_price",
                    data={"error": "No price data available"},
                    timestamp=datetime.now(),
                ),
            )

    async def _handle_get_price_history(
        self, connection_id: str, params: Dict[str, Any]
    ) -> None:
        """Handle request for price history"""
        limit = min(params.get("limit", 100), 1000)  # Max 1000 records

        history = self._price_history[-limit:] if self._price_history else []

        await self.send_message(
            connection_id,
            WebSocketMessage(
                type="price_history",
                data={"history": history, "count": len(history)},
                timestamp=datetime.now(),
            ),
        )

    async def _send_price_history(self, connection_id: str) -> None:
        """Send recent price history to new connection"""
        if self._price_history:
            # Send last 50 price points
            recent_history = self._price_history[-50:]

            await self.send_message(
                connection_id,
                WebSocketMessage(
                    type="price_history",
                    data={"history": recent_history, "count": len(recent_history)},
                    timestamp=datetime.now(),
                ),
            )

    async def _handle_start_streaming(self, connection_id: str) -> None:
        """Handle start streaming request"""
        logger.info(f"🎯 Starting streaming for connection: {connection_id}")

        # Send confirmation message
        await self.send_message(
            connection_id,
            WebSocketMessage(
                type="streaming_started",
                data={"status": "streaming_started"},
                timestamp=datetime.now(),
            ),
        )

        # Update connection info
        if connection_id in self.connection_info:
            self.connection_info[connection_id].is_active = True

    async def _handle_stop_streaming(self, connection_id: str) -> None:
        """Handle stop streaming request"""
        logger.info(f"🛑 Stopping streaming for connection: {connection_id}")

        # Send confirmation message
        await self.send_message(
            connection_id,
            WebSocketMessage(
                type="streaming_stopped",
                data={"status": "streaming_stopped"},
                timestamp=datetime.now(),
            ),
        )

        # Update connection info
        if connection_id in self.connection_info:
            self.connection_info[connection_id].is_active = False

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of stale connections"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                now = datetime.now()
                stale_connections = []

                for connection_id, info in self.connection_info.items():
                    # Check if connection is stale (no ping for 5 minutes)
                    last_activity = info.last_ping or info.connected_at
                    if (now - last_activity).total_seconds() > 300:
                        stale_connections.append(connection_id)

                # Clean up stale connections
                for connection_id in stale_connections:
                    logger.info(f"🧹 Cleaning up stale connection: {connection_id}")
                    await self.disconnect(connection_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in cleanup loop: {e}")

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": len(self.connections),
            "active_connections": len(
                [info for info in self.connection_info.values() if info.is_active]
            ),
            "price_history_count": len(self._price_history),
            "connections": [
                {
                    "id": info.id,
                    "connected_at": info.connected_at.isoformat(),
                    "last_ping": info.last_ping.isoformat() if info.last_ping else None,
                    "is_active": info.is_active,
                }
                for info in self.connection_info.values()
            ],
        }
