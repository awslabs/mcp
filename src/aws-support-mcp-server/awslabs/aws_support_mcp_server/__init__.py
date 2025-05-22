"""AWS Support MCP Server package."""

import logging
import sys

from loguru import logger

# Configure package-level logging
logger.remove()
logger.add(
    sys.stderr,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)

# Export version
__version__ = "0.1.0"
