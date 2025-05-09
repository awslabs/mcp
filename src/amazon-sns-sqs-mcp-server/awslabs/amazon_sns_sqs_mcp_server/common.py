"""Common utilities for MCP server."""
from typing import Dict, Tuple


# Tag name constant
MCP_SERVER_VERSION_TAG = 'mcp_server_version'

def validate_mcp_server_version_tag(tags: Dict[str, str]) -> Tuple[bool, str]:
    """Check if the tags contain the mcp_server_version tag.

    Args:
        tags: Dictionary where keys are tag names and values are tag values

    Returns:
        Tuple of (is_valid, error_message)

    """
    return (True, "") if MCP_SERVER_VERSION_TAG in tags else (False, 'mutating a resource without the mcp_server_version tag is not allowed')
