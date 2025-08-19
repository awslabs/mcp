"""
Type definitions for the MCP testing framework.
"""

from enum import Enum


class TestType(Enum):
    """Enum for different types of MCP tests."""
    TOOL_CALL = "tool_call"
    RESOURCE_READ = "resource_read"
    PROMPT_GET = "prompt_get"


# Prevent pytest from collecting this as a test class
TestType.__test__ = False
