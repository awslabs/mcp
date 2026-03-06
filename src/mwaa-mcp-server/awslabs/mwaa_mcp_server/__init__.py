"""MWAA MCP Server - Model Context Protocol server for Amazon Managed Workflows for Apache Airflow."""

from .server import mcp
from .tools import MWAATools

__all__ = ["mcp", "MWAATools"]
__version__ = "0.1.0"
