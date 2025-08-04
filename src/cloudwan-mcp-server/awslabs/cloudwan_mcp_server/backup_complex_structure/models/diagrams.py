"""
Diagram-specific data models for CloudWAN MCP Server.

This module provides imports for diagram-related network models.
For backward compatibility, it re-exports models from the network module.
"""

# Re-export core network models for diagram usage
from .network import (
    NetworkElement,
    NetworkElementType,
    NetworkConnection,
    ConnectionType,
    NetworkTopology,
)

__all__ = [
    "NetworkElement",
    "NetworkElementType", 
    "NetworkConnection",
    "ConnectionType",
    "NetworkTopology",
]