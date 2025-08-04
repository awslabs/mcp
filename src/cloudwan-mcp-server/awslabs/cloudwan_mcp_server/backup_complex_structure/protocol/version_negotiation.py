"""
MCP Version Negotiation Module.

This module provides the MCPVersionNegotiator class that was previously in negotiation.py
but is needed as a separate import for backward compatibility.
"""

try:
    from negotiation import (
        ProtocolNegotiator as MCPVersionNegotiator,
        ProtocolConfiguration,
        ProtocolCapabilities,
        initialize_protocol,
        get_protocol_negotiator,
        negotiate_protocol_version,
        is_protocol_feature_supported,
        get_protocol_info,
    )

    _NEGOTIATION_AVAILABLE = True
except ImportError:
    try:
        from .negotiation import (
            ProtocolNegotiator as MCPVersionNegotiator,
            ProtocolConfiguration,
            ProtocolCapabilities,
            initialize_protocol,
            get_protocol_negotiator,
            negotiate_protocol_version,
            is_protocol_feature_supported,
            get_protocol_info,
        )

        _NEGOTIATION_AVAILABLE = True
    except ImportError:
        _NEGOTIATION_AVAILABLE = False

if _NEGOTIATION_AVAILABLE:
    __all__ = [
        "MCPVersionNegotiator",
        "ProtocolConfiguration",
        "ProtocolCapabilities",
        "initialize_protocol",
        "get_protocol_negotiator",
        "negotiate_protocol_version",
        "is_protocol_feature_supported",
        "get_protocol_info",
    ]
else:
    __all__ = []
