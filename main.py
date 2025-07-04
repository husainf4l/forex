from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
from typing import Dict, Optional, List
from datetime import datetime
import json
import asyncio
from capital_api import CapitalAPI

app = FastAPI(title="Gold Analyzer", description="Live Gold Price from Capital.com")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize Capital.com API
capital_api = CapitalAPI(demo=False)  # Use production environment


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.gold_price_data = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(
            f"🔗 New WebSocket connection. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(
            f"🔌 WebSocket disconnected. Total connections: {len(self.active_connections)}"
        )

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

    async def broadcast_gold_price(self, price_data: dict):
        """Broadcast gold price updates to all connected clients"""
        self.gold_price_data = price_data
        message = json.dumps({"type": "gold_price_update", "data": price_data})
        await self.broadcast(message)


manager = ConnectionManager()


# Callback function for price updates from WebSocket
def on_price_update(price_data: dict):
    """Callback function to handle price updates from Capital.com WebSocket"""
    print(f"📊 Price update received: {price_data}")
    # Schedule the broadcast to run in the main event loop
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(manager.broadcast_gold_price(price_data))
    else:
        # If no event loop is running, we can't broadcast
        print("⚠️ No event loop running, unable to broadcast price update")


# Register the callback
capital_api.add_price_callback(on_price_update)


# Test login on startup
@app.on_event("startup")
async def startup_event():
    """Initialize API connection on startup"""
    print("🚀 Starting Gold Analyzer application...")
    login_success = capital_api.login()
    if login_success:
        print("✅ Capital.com API authentication successful!")
        print("🎯 Application ready to serve gold price data!")

        # Start WebSocket streaming for real-time prices
        capital_api.start_websocket_stream()
        print("📡 Real-time gold price streaming started!")
    else:
        print("❌ Capital.com API authentication failed!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("🛑 Shutting down Gold Analyzer application...")
    capital_api.stop_websocket_stream()
    print("👋 Application shutdown complete!")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the main gold analysis dashboard page"""
    return templates.TemplateResponse("clean.html", {"request": request})


@app.websocket("/ws/gold-prices")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time gold price updates"""
    await manager.connect(websocket)

    try:
        # Send current gold price data if available
        if manager.gold_price_data:
            await manager.send_personal_message(
                json.dumps(
                    {"type": "gold_price_update", "data": manager.gold_price_data}
                ),
                websocket,
            )

        # Send connection status
        await manager.send_personal_message(
            json.dumps(
                {
                    "type": "connection_status",
                    "status": "connected",
                    "websocket_streaming": capital_api.is_websocket_connected(),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            websocket,
        )

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle different message types
                if message.get("type") == "ping":
                    await manager.send_personal_message(
                        json.dumps(
                            {"type": "pong", "timestamp": datetime.now().isoformat()}
                        ),
                        websocket,
                    )
                elif message.get("type") == "get_current_price":
                    # Send current price data
                    if manager.gold_price_data:
                        await manager.send_personal_message(
                            json.dumps(
                                {
                                    "type": "gold_price_update",
                                    "data": manager.gold_price_data,
                                }
                            ),
                            websocket,
                        )

            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"❌ WebSocket error: {e}")
                break

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected")
    except Exception as e:
        print(f"❌ WebSocket connection error: {e}")
        manager.disconnect(websocket)


@app.get("/api/gold-live")
async def get_live_gold_data():
    """Get live GOLD data from Capital.com"""
    try:
        gold_data = capital_api.get_gold_price()
        if gold_data:
            return {
                "success": True,
                "data": gold_data,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "error": "Failed to fetch gold data",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/api/gold-info")
async def get_gold_market_info():
    """Get GOLD market information from Capital.com"""
    try:
        market_info = capital_api.get_market_info()
        if market_info:
            return {
                "success": True,
                "data": market_info,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "error": "Failed to fetch market info",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/api/websocket-status")
async def websocket_status():
    """Get WebSocket connection status"""
    return {
        "websocket_connected": capital_api.is_websocket_connected(),
        "active_connections": len(manager.active_connections),
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
