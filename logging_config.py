"""
Logging configuration for eTrade Dashboard.
Provides Vercel-compatible console logging with environment-aware log levels.
"""

import logging
import sys
from config import FLASK_DEBUG


def setup_logging() -> logging.Logger:
    """
    Configure and return the root application logger.

    - Production (FLASK_DEBUG=False): INFO level, concise output
    - Development (FLASK_DEBUG=True): DEBUG level, verbose output
    """
    logger = logging.getLogger('etrade_dashboard')

    # Prevent duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    # Set level based on environment
    log_level = logging.DEBUG if FLASK_DEBUG else logging.INFO
    logger.setLevel(log_level)

    # Console handler (stdout for Vercel compatibility)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Format based on environment
    if FLASK_DEBUG:
        # Verbose format for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Concise format for production (Vercel adds timestamps)
        formatter = logging.Formatter(
            '%(levelname)s - %(name)s - %(message)s'
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a child logger for a specific module.

    Args:
        name: Module name (e.g., 'api', 'auth', 'db')

    Returns:
        Logger instance with name 'etrade_dashboard.{name}'
    """
    # Ensure root logger is configured
    setup_logging()
    return logging.getLogger(f'etrade_dashboard.{name}')
