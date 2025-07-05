"""
Logging configuration for the Gold Trading Dashboard
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from .config import settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
) -> None:
    """
    Setup application logging with console and file handlers

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        max_bytes: Maximum log file size in bytes
        backup_count: Number of backup log files to keep
    """

    # Determine log level
    level = getattr(logging, (log_level or settings.LOG_LEVEL).upper(), logging.INFO)

    # Create custom formatter
    formatter = logging.Formatter(fmt=settings.LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if log_file specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Configure third-party loggers
    configure_third_party_loggers(level)

    # Log the configuration
    logger = logging.getLogger("app.logging")
    logger.info(f"🔧 Logging configured - Level: {logging.getLevelName(level)}")
    if log_file:
        logger.info(f"📁 Log file: {log_file}")


def configure_third_party_loggers(level: int) -> None:
    """Configure logging levels for third-party libraries"""

    # Set higher log levels for noisy third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    # Keep our app loggers at the configured level
    logging.getLogger("app").setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
