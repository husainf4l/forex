from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
from typing import Dict, Optional
from datetime import datetime
from capital_api import CapitalAPI

app = FastAPI(title="Gold Analyzer", description="Live Gold Price from Capital.com")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize Capital.com API
capital_api = CapitalAPI(demo=False)  # Use production environment

# Test login on startup
@app.on_event("startup")
async def startup_event():
    """Initialize API connection on startup"""
    print("🚀 Starting Gold Analyzer application...")
    login_success = capital_api.login()
    if login_success:
        print("✅ Capital.com API authentication successful!")
    else:
        print("❌ Capital.com API authentication failed!")
        
    # Test getting account info
    if login_success:
        account_info = capital_api.get_account_info()
        if account_info:
            print(f"💰 Account Balance: {account_info.get('balance', 'N/A')}")
            print(f"💵 Currency: {account_info.get('currency', 'N/A')}")
        else:
            print("❌ Failed to get account info")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the main gold analysis dashboard page"""
    return templates.TemplateResponse("clean.html", {"request": request})

@app.get("/api/gold-live")
async def get_live_gold_data():
    """Get live GOLD data from Capital.com"""
    try:
        gold_data = capital_api.get_gold_price()
        if gold_data:
            return {
                "success": True,
                "data": gold_data,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": "Failed to fetch gold data",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
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
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": "Failed to fetch market info",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
