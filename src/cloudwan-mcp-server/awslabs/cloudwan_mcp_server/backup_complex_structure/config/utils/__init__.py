"""
Utility functions for CloudWAN MCP configuration.
"""

import os
from typing import Optional

from ..main_config import CloudWANConfig


def get_default_config() -> CloudWANConfig:
    """
    Get default configuration with sensible defaults.

    Returns:
        CloudWANConfig: Default configuration instance
    """
    return CloudWANConfig()


def load_config_from_env() -> CloudWANConfig:
    """
    Load configuration from environment variables.

    Returns:
        CloudWANConfig: Configuration loaded from environment
    """
    # Environment variables are loaded automatically by Pydantic BaseSettings
    return CloudWANConfig()


__all__ = [
    "get_default_config",
    "load_config_from_env",
]
