"""
WebSocket Configuration for CloudWAN MCP Real-time Alerting.

This module provides configuration options for WebSocket server settings
including host, port, authentication, and security options.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Any, Callable


@dataclass
class WebSocketConfig:
    """WebSocket server configuration"""

    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8765
    require_authentication: bool = False
    auth_handler: Optional[Callable] = None
    heartbeat_interval_seconds: int = 15
    connection_timeout_seconds: int = 60
    max_connections: int = 1000
    max_message_size: int = 65536  # 64KB
    ssl_enabled: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None

    # Advanced options
    compression_enabled: bool = True
    ping_interval: int = 20
    ping_timeout: int = 20
    close_timeout: int = 10
    max_queue_size: int = 32

    # Features
    subscription_management_enabled: bool = True
    connection_health_monitoring_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        result = {}
        for field_name, field_value in self.__dict__.items():
            # Skip callable objects
            if not callable(field_value):
                result[field_name] = field_value
        return result

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "WebSocketConfig":
        """Create configuration from dictionary"""
        # Filter out unknown fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_dict = {k: v for k, v in config_dict.items() if k in known_fields}
        return cls(**filtered_dict)


# Default configuration
DEFAULT_WEBSOCKET_CONFIG = WebSocketConfig()
