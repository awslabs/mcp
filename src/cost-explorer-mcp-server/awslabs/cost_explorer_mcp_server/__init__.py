"""
Cost Explorer MCP Server module.

This module provides MCP tools for analyzing AWS costs and usage data through the AWS Cost Explorer API.
"""

from awslabs.cost_explorer_mcp_server.server import app

__all__ = ["app"]
