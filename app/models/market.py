"""
Pydantic models for gold price data
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class PriceType(str, Enum):
    """Price types"""

    BID = "bid"
    ASK = "ask"
    MID = "mid"


class TimeFrame(str, Enum):
    """Chart timeframes"""

    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1D"


class MarketStatus(str, Enum):
    """Market status"""

    OPEN = "open"
    CLOSED = "closed"
    WEEKEND = "weekend"


class PriceTick(BaseModel):
    """Individual price tick"""

    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    mid: Optional[float] = None
    volume: Optional[int] = None

    @property
    def price(self) -> Optional[float]:
        """Get the most relevant price"""
        return self.mid or self.ask or self.bid


class OHLC(BaseModel):
    """OHLC candlestick data"""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int] = None
    timeframe: TimeFrame


class MarketData(BaseModel):
    """Complete market data"""

    symbol: str = "XAU/USD"
    current_price: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    change_24h: Optional[float] = None
    change_percent_24h: Optional[float] = None
    volume_24h: Optional[int] = None
    last_update: Optional[datetime] = None
    market_status: MarketStatus = MarketStatus.CLOSED


class WebSocketMessage(BaseModel):
    """WebSocket message structure"""

    type: str
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None


class ConnectionInfo(BaseModel):
    """WebSocket connection information"""

    id: str
    connected_at: datetime
    last_ping: Optional[datetime] = None
    is_active: bool = True
