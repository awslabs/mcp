"""
AWS Database Migration Service (DMS) MCP Server.

A Model Context Protocol server providing natural language access to AWS DMS operations.
Built on FastMCP framework with comprehensive type safety and validation.
"""

from .server import create_server
from .config import DMSServerConfig

__version__ = '0.0.1'
__all__ = ['create_server', 'DMSServerConfig', '__version__']
