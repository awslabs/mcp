"""
Configuration utilities for the ECS MCP Server.
"""

import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


def get_config() -> Dict[str, Any]:
    """
    Gets the configuration for the ECS MCP Server.

    Returns:
        Dict containing configuration values
    """
    config = {
        "aws_region": os.environ.get("AWS_REGION", "us-east-1"),
        "aws_profile": os.environ.get("AWS_PROFILE", None),
        "log_level": os.environ.get("FASTMCP_LOG_LEVEL", "INFO"),
        "log_file": os.environ.get("FASTMCP_LOG_FILE"),
        # Security settings via environment variables
        "allow-write": os.environ.get("ALLOW_WRITE", "").lower() in ("true", "1", "yes"),
        "allow-sensitive-data": os.environ.get("ALLOW_SENSITIVE_DATA", "").lower()
        in ("true", "1", "yes"),
    }

    logger.debug(f"Loaded configuration: {config}")
    return config
