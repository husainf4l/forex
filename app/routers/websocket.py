"""
WebSocket router for real-time connections
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from ..dependencies import get_websocket_manager
from ..services.websocket import WebSocketManager
from ..core.logging import get_logger

logger = get_logger(__name__)

websocket_router = APIRouter()


@websocket_router.websocket("/gold-prices")
async def websocket_endpoint(
    websocket: WebSocket, ws_manager: WebSocketManager = Depends(get_websocket_manager)
):
    """WebSocket endpoint for real-time gold prices"""
    connection_id = None

    try:
        # Accept connection
        connection_id = await ws_manager.connect(websocket)

        # Listen for messages
        while True:
            message = await websocket.receive_text()
            await ws_manager.handle_client_message(connection_id, message)

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket client disconnected: {connection_id}")

    except Exception as e:
        logger.error(f"❌ WebSocket error for {connection_id}: {e}")

    finally:
        if connection_id:
            await ws_manager.disconnect(connection_id)
