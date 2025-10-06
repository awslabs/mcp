"""
Data models for AWS DMS MCP Server.

Pydantic models for type-safe data validation and serialization.
"""

from .config_models import (
    ReplicationInstanceConfig,
    EndpointConfig,
    TaskConfig,
)
from .dms_models import (
    ReplicationInstanceResponse,
    EndpointResponse,
    TaskResponse,
    TableStatistics,
    PaginationConfig,
    FilterConfig,
    OperationResponse,
    ErrorResponse,
)

__all__ = [
    # Configuration Models
    "ReplicationInstanceConfig",
    "EndpointConfig",
    "TaskConfig",
    # Response Models
    "ReplicationInstanceResponse",
    "EndpointResponse",
    "TaskResponse",
    "TableStatistics",
    # Common Models
    "PaginationConfig",
    "FilterConfig",
    "OperationResponse",
    "ErrorResponse",
]