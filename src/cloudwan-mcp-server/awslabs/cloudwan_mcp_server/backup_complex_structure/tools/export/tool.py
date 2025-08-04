"""
Network Data Export Tool for CloudWAN MCP Server.

This module provides an MCP tool interface for exporting CloudWAN network data
in various formats with filtering capabilities.
"""

import json
import logging
from typing import Dict, List, Optional, Any

from mcp.types import TextContent

from ...aws.client_manager import AWSClientManager
from ...config import CloudWANConfig
from ..base_enhanced import BaseMCPTool, handle_mcp_errors
from ..base import handle_aws_errors
from .engine import NetworkDataExportEngine
from .models import (
    NetworkDataExportFormat,
    NetworkDataType,
    ExportRequest,
    NetworkDataFilter,
)


class NetworkDataExportTool(BaseMCPTool):
    """
    Network data export tool for CloudWAN MCP.

    Provides comprehensive capabilities to export network data in various formats,
    with support for filtering, region selection, and custom output paths.
    """

    def __init__(self, aws_manager: AWSClientManager, config: Optional[CloudWANConfig] = None):
        """Initialize the export tool."""
        super().__init__(aws_manager, config or CloudWANConfig())
        self._tool_name = "export_network_data"
        self._description = (
            "Export AWS CloudWAN network data in various formats including JSON, CSV, "
            "YAML, Excel, and more. Supports detailed filtering and region selection."
        )

        self.export_engine = NetworkDataExportEngine(aws_manager, config)
        self.logger = logging.getLogger(__name__)

    @property
    def tool_name(self) -> str:
        """Get the tool name."""
        return self._tool_name

    @property
    def description(self) -> str:
        """Get the tool description."""
        return self._description

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the tool input schema."""
        return {
            "type": "object",
            "properties": {
                "data_type": {
                    "type": "string",
                    "enum": [t.value for t in NetworkDataType],
                    "description": "Type of network data to export",
                    "default": "topology",
                },
                "format": {
                    "type": "string",
                    "enum": [f.value for f in NetworkDataExportFormat],
                    "description": "Export format",
                    "default": "json",
                },
                "regions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "AWS regions to include (default: all configured regions)",
                    "default": [],
                },
                "output_path": {
                    "type": "string",
                    "description": "Output file path (optional, default: auto-generated in current directory)",
                    "default": "",
                },
                "filters": {
                    "type": "object",
                    "description": "Data filtering options",
                    "properties": {
                        "include_vpcs": {
                            "type": "boolean",
                            "description": "Include VPC data",
                            "default": True,
                        },
                        "include_subnets": {
                            "type": "boolean",
                            "description": "Include subnet data",
                            "default": True,
                        },
                        "include_route_tables": {
                            "type": "boolean",
                            "description": "Include route table data",
                            "default": True,
                        },
                        "include_security_groups": {
                            "type": "boolean",
                            "description": "Include security group data",
                            "default": True,
                        },
                        "include_tgw_attachments": {
                            "type": "boolean",
                            "description": "Include Transit Gateway attachments",
                            "default": True,
                        },
                        "include_cloudwan_attachments": {
                            "type": "boolean",
                            "description": "Include CloudWAN attachments",
                            "default": True,
                        },
                        "include_policies": {
                            "type": "boolean",
                            "description": "Include policy documents",
                            "default": True,
                        },
                        "include_performance_metrics": {
                            "type": "boolean",
                            "description": "Include performance metrics",
                            "default": False,
                        },
                        "include_metadata": {
                            "type": "boolean",
                            "description": "Include metadata in export",
                            "default": True,
                        },
                        "resource_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by specific resource IDs",
                            "default": [],
                        },
                        "vpc_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by specific VPC IDs",
                            "default": [],
                        },
                        "segment_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by segment names",
                            "default": [],
                        },
                        "attachment_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by attachment types",
                            "default": [],
                        },
                        "cidr_blocks": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by CIDR blocks",
                            "default": [],
                        },
                    },
                },
                "source_ip": {
                    "type": "string",
                    "description": "Source IP for path trace export (required for PATH_TRACE data type)",
                },
                "destination_ip": {
                    "type": "string",
                    "description": "Destination IP for path trace export (required for PATH_TRACE data type)",
                },
                "protocol": {
                    "type": "string",
                    "description": "Protocol for path trace export (tcp, udp, icmp)",
                    "default": "tcp",
                },
                "port": {
                    "type": "integer",
                    "description": "Port for path trace export",
                    "default": 443,
                },
                "use_streaming": {
                    "type": "boolean",
                    "description": "Use streaming mode for large datasets (better performance and memory usage)",
                    "default": false,
                },
                "chunk_size": {
                    "type": "integer",
                    "description": "Chunk size for streaming exports",
                    "default": 100,
                },
                "encrypt_output": {
                    "type": "boolean",
                    "description": "Encrypt the output file with AES-256 encryption",
                    "default": false,
                },
                "add_integrity_signature": {
                    "type": "boolean",
                    "description": "Add integrity signature to verify file hasn't been tampered with",
                    "default": true,
                },
                "allowed_export_directories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Allowed directories for export (empty allows all directories)",
                    "default": [],
                },
            },
            "required": ["data_type", "format"],
        }

    @handle_mcp_errors
    @handle_aws_errors("Network data export")
    async def execute(self, **kwargs) -> List[TextContent]:
        """Execute network data export."""
        try:
            # Parse arguments
            data_type = NetworkDataType(kwargs.get("data_type", "topology"))
            export_format = NetworkDataExportFormat(kwargs.get("format", "json"))
            regions = kwargs.get("regions", [])
            output_path = kwargs.get("output_path", "")

            # Create filters object
            filters_dict = kwargs.get("filters", {})

            # Special handling for path trace
            if data_type == NetworkDataType.PATH_TRACE:
                # Set source_ip and destination_ip in filters if provided
                if "source_ip" in kwargs and "destination_ip" in kwargs:
                    filters_dict["source_ip"] = kwargs["source_ip"]
                    filters_dict["destination_ip"] = kwargs["destination_ip"]
                    filters_dict["protocol"] = kwargs.get("protocol", "tcp")
                    filters_dict["port"] = kwargs.get("port", 443)
                else:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "success": False,
                                    "error": "source_ip and destination_ip are required for path trace export",
                                },
                                indent=2,
                            ),
                        )
                    ]

            # Check for streaming option based on data size
            use_streaming = kwargs.get("use_streaming", False)

            # Auto-enable streaming for large datasets across multiple regions
            if not use_streaming:
                large_data_types = ["topology", "routes", "security_groups", "vpcs"]
                if data_type.value in large_data_types and len(regions) > 2:
                    self.logger.info(
                        f"Auto-enabling streaming mode for large dataset: {data_type.value} across {len(regions)} regions"
                    )
                    use_streaming = True

            filters = NetworkDataFilter(**filters_dict)

            # Extract security-related parameters
            encrypt_output = kwargs.get("encrypt_output", False)
            add_integrity_signature = kwargs.get("add_integrity_signature", True)
            allowed_export_directories = kwargs.get("allowed_export_directories", [])

            # Create export request
            request = ExportRequest(
                data_type=data_type,
                format=export_format,
                regions=regions,
                output_path=output_path,
                filters=filters,
                source_ip=kwargs.get("source_ip"),
                destination_ip=kwargs.get("destination_ip"),
                protocol=kwargs.get("protocol", "tcp"),
                port=kwargs.get("port", 443),
                use_streaming=use_streaming,
                chunk_size=kwargs.get("chunk_size", 100),
                encrypt_output=encrypt_output,
                add_integrity_signature=add_integrity_signature,
                allowed_export_directories=allowed_export_directories,
            )

            # Execute export
            self.logger.info(
                f"Starting data export: type={data_type.value}, format={export_format.value}, "
                f"streaming={use_streaming}, encrypted={encrypt_output}"
            )
            result = await self.export_engine.export_data(request)

            # Return response
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"success": False, "error": str(e)}, indent=2),
                )
            ]
