"""
Export data models for CloudWAN MCP Server.

This module contains Pydantic models for exporting network data in various formats,
including enums for export formats and data types, request parameters, and response models.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from ...models.base import BaseResponse


class NetworkDataExportFormat(str, Enum):
    """Supported export formats for network data."""

    JSON = "json"
    CSV = "csv"
    YAML = "yaml"
    EXCEL = "excel"
    MARKDOWN = "markdown"
    HTML = "html"
    XML = "xml"


class NetworkDataType(str, Enum):
    """Types of network data that can be exported."""

    TOPOLOGY = "topology"
    ROUTES = "routes"
    SEGMENT_ROUTES = "segment_routes"
    ATTACHMENTS = "attachments"
    PATH_TRACE = "path_trace"
    BGP_SESSIONS = "bgp_sessions"
    TRANSIT_GATEWAY_ROUTES = "tgw_routes"
    SECURITY_GROUPS = "security_groups"
    CORE_NETWORKS = "core_networks"
    VPCS = "vpcs"


class NetworkDataFilter(BaseModel):
    """Filter criteria for network data export."""

    include_vpcs: bool = Field(default=True, description="Include VPC data")
    include_subnets: bool = Field(default=True, description="Include subnet data")
    include_route_tables: bool = Field(default=True, description="Include route table data")
    include_security_groups: bool = Field(default=True, description="Include security group data")
    include_tgw_attachments: bool = Field(
        default=True, description="Include Transit Gateway attachments"
    )
    include_cloudwan_attachments: bool = Field(
        default=True, description="Include CloudWAN attachments"
    )
    include_policies: bool = Field(default=True, description="Include policy documents")
    include_performance_metrics: bool = Field(
        default=False, description="Include performance metrics"
    )
    include_metadata: bool = Field(default=True, description="Include metadata in export")
    resource_ids: List[str] = Field(
        default_factory=list, description="Filter by specific resource IDs"
    )
    vpc_ids: List[str] = Field(default_factory=list, description="Filter by specific VPC IDs")
    segment_names: List[str] = Field(default_factory=list, description="Filter by segment names")
    attachment_types: List[str] = Field(
        default_factory=list, description="Filter by attachment types"
    )
    cidr_blocks: List[str] = Field(default_factory=list, description="Filter by CIDR blocks")


class ExportRequest(BaseModel):
    """Network data export request model."""

    data_type: NetworkDataType = Field(description="Type of network data to export")
    format: NetworkDataExportFormat = Field(description="Export format")
    regions: List[str] = Field(
        default_factory=list,
        description="AWS regions to include (default: all configured regions)",
    )
    output_path: Optional[str] = Field(
        default=None,
        description="Output file path (optional, default: auto-generated in current directory)",
    )
    filters: NetworkDataFilter = Field(
        default_factory=NetworkDataFilter, description="Data filtering options"
    )
    source_ip: Optional[str] = Field(default=None, description="Source IP for path trace export")
    destination_ip: Optional[str] = Field(
        default=None, description="Destination IP for path trace export"
    )
    protocol: str = Field(default="tcp", description="Protocol for path trace export")
    port: int = Field(default=443, description="Port for path trace export")
    use_streaming: bool = Field(default=False, description="Use streaming mode for large datasets")
    chunk_size: int = Field(default=100, description="Chunk size for streaming exports")
    encrypt_output: bool = Field(default=False, description="Encrypt the output file")
    add_integrity_signature: bool = Field(
        default=True, description="Add integrity signature to the output"
    )
    allowed_export_directories: List[str] = Field(
        default_factory=list,
        description="Allowed directories for export (empty list allows all)",
    )


class NetworkDataExportResponse(BaseResponse):
    """Response model for network data export."""

    data_type: NetworkDataType = Field(description="Type of network data exported")
    export_format: NetworkDataExportFormat = Field(description="Format of the export")
    output_path: Optional[str] = Field(default=None, description="Path to the exported file")
    file_size_bytes: Optional[int] = Field(
        default=None, description="Size of the exported file in bytes"
    )
    element_count: Optional[int] = Field(
        default=None, description="Number of elements in the export"
    )
    regions: List[str] = Field(default_factory=list, description="Regions included in the export")
    execution_time_ms: Optional[int] = Field(
        default=None, description="Time taken to execute the export in milliseconds"
    )
    success: bool = Field(default=True, description="Whether the export was successful")
    warnings: List[str] = Field(
        default_factory=list, description="Warnings encountered during export"
    )
    errors: List[str] = Field(default_factory=list, description="Errors encountered during export")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata about the export"
    )
    encrypted: bool = Field(default=False, description="Whether the output file is encrypted")
    integrity_signature: Optional[str] = Field(default=None, description="File integrity signature")
