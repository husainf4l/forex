"""
Application configuration and settings
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings"""

    # App Config
    APP_NAME: str = Field(default="Gold Trading Dashboard", env="APP_NAME")
    APP_DESCRIPTION: str = Field(
        default="Professional real-time gold trading analysis platform",
        env="APP_DESCRIPTION",
    )
    APP_VERSION: str = Field(default="2.0.0", env="APP_VERSION")
    DEBUG: bool = Field(default=False, env="DEBUG")

    # Server Config
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")

    # Logging Config
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT"
    )

    # Capital.com API Config
    CAPITAL_API_KEY: str = Field(..., env="CAPITAL_API_KEY")
    CAPITAL_EMAIL: str = Field(..., env="CAPITAL_EMAIL")
    CAPITAL_PASSWORD: str = Field(..., env="CAPITAL_PASSWORD")
    CAPITAL_DEMO: bool = Field(default=False, env="CAPITAL_DEMO")
    CAPITAL_BASE_URL: Optional[str] = Field(default=None, env="CAPITAL_BASE_URL")
    CAPITAL_WEBSOCKET_URL: Optional[str] = Field(
        default=None, env="CAPITAL_WEBSOCKET_URL"
    )

    # WebSocket Config
    WEBSOCKET_PING_INTERVAL: int = Field(default=30, env="WS_PING_INTERVAL")
    WEBSOCKET_PING_TIMEOUT: int = Field(default=10, env="WS_PING_TIMEOUT")
    WEBSOCKET_MAX_CONNECTIONS: int = Field(default=100, env="MAX_CONNECTIONS")

    # Market Data Config
    GOLD_SYMBOL: str = Field(default="GOLD", env="GOLD_SYMBOL")
    DEFAULT_TIMEFRAME: str = Field(default="1m", env="DEFAULT_TIMEFRAME")
    MAX_HISTORICAL_CANDLES: int = Field(default=1000, env="MAX_HISTORICAL_CANDLES")
    MAX_PRICE_HISTORY: int = Field(default=1000, env="MAX_PRICE_HISTORY")
    DATA_RETENTION_HOURS: int = Field(default=24, env="DATA_RETENTION_HOURS")

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")

    # Database Config
    DATABASE_HOST: str = Field(..., env="DATABASE_HOST")
    DATABASE_USER: str = Field(..., env="DATABASE_USER")
    DATABASE_PASSWORD: str = Field(..., env="DATABASE_PASSWORD")
    DATABASE_NAME: str = Field(..., env="DATABASE_NAME")
    DATABASE_PORT: int = Field(default=5432, env="DATABASE_PORT")
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
