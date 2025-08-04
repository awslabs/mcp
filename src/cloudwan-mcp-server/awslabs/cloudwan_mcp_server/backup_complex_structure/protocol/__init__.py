"""
MCP Protocol compliance and error handling module.

This module provides comprehensive MCP protocol compliance including:
- AWS exception to MCP error code mapping
- MCP heartbeat mechanism implementation
- Protocol version negotiation
- Structured error responses
- WebSocket server for real-time alerting
- WebSocket alert notification system
"""

import logging

logger = logging.getLogger(__name__)

# Core protocol components that don't require external dependencies
try:
    from .error_mapping import (
        MCPErrorCode,
        MCPError,
        AWSToMCPErrorMapper,
        ToolError,
        map_aws_error_to_mcp,
    )

    _ERROR_MAPPING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Error mapping not available: {e}")
    _ERROR_MAPPING_AVAILABLE = False

try:
    from .heartbeat import MCPHeartbeatManager

    _HEARTBEAT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Heartbeat manager not available: {e}")
    _HEARTBEAT_AVAILABLE = False

try:
    from .version_negotiation import MCPVersionNegotiator

    _VERSION_NEGOTIATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Version negotiation not available: {e}")
    _VERSION_NEGOTIATION_AVAILABLE = False

try:
    from .protocol_handler import MCPProtocolHandler

    _PROTOCOL_HANDLER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Protocol handler not available: {e}")
    _PROTOCOL_HANDLER_AVAILABLE = False

# WebSocket components (may require additional dependencies)
try:
    from .websocket_server import (
        WebSocketServer,
        WebSocketConnection,
        WebSocketMessage,
        AlertMessage,
        ConnectionState,
    )

    _WEBSOCKET_SERVER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"WebSocket server not available: {e}")
    _WEBSOCKET_SERVER_AVAILABLE = False

try:
    from .websocket_alert_notifier import WebSocketAlertNotifier

    _WEBSOCKET_NOTIFIER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"WebSocket alert notifier not available: {e}")
    _WEBSOCKET_NOTIFIER_AVAILABLE = False

# Build __all__ list dynamically based on what's available
__all__ = []

if _ERROR_MAPPING_AVAILABLE:
    __all__.extend(
        [
            "MCPErrorCode",
            "MCPError",
            "AWSToMCPErrorMapper",
            "ToolError",
            "map_aws_error_to_mcp",
        ]
    )

if _HEARTBEAT_AVAILABLE:
    __all__.append("MCPHeartbeatManager")

if _VERSION_NEGOTIATION_AVAILABLE:
    __all__.append("MCPVersionNegotiator")

if _PROTOCOL_HANDLER_AVAILABLE:
    __all__.append("MCPProtocolHandler")

if _WEBSOCKET_SERVER_AVAILABLE:
    __all__.extend(
        [
            "WebSocketServer",
            "WebSocketConnection",
            "WebSocketMessage",
            "AlertMessage",
            "ConnectionState",
        ]
    )

if _WEBSOCKET_NOTIFIER_AVAILABLE:
    __all__.append("WebSocketAlertNotifier")
