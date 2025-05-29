"""
Template utilities for the ECS MCP Server.
"""

import logging
import os

logger = logging.getLogger(__name__)


def get_templates_dir() -> str:
    """
    Gets the path to the templates directory.

    Returns:
        Path to the templates directory
    """
    templates_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"
    )

    if not os.path.isdir(templates_dir):
        logger.error(f"Templates directory not found at {templates_dir}")
        raise FileNotFoundError(f"Templates directory not found at {templates_dir}")

    return templates_dir
