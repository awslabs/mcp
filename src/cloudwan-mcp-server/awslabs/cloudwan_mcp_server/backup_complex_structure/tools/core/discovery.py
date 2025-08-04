import socket
import ipaddress
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Any
import asyncio
from botocore.exceptions import ClientError, ParamValidationError

from mcp.types import Tool, TextContent, CallToolResult

from ...aws.client_manager import AWSClientManager
from ...config import CloudWANConfig
from ...models.network import GlobalNetworkInfo, CoreNetworkInfo, GlobalNetworksResponse
from ...utils.aws_operations import handle_aws_errors, semaphore_manager
from ...utils.response_validation import response_validator
from ...utils.aws_wrapper import AWSOperation

from ..base import BaseMCPTool

class CoreNetworkDiscoveryTool(BaseMCPTool):
    """Tool for Core Network discovery."""

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig = None):
        super().__init__(aws_manager, config or CloudWANConfig())
        self._tool_name = "list_core_networks"
        self._description = "Discover Core Networks across global networks with detailed policy information"

    @property
    def tool_name(self) -> str:
        return self._tool_name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "global_network_id": {
                    "type": "string",
                    "description": "Global Network ID to search (optional - searches all if not provided)",
                },
                "include_policies": {
                    "type": "boolean",
                    "description": "Include policy documents in response",
                    "default": True,
                },
            },
            "required": [],
        }

    def _normalize_arguments(self, arguments: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Normalize arguments with multiple levels of nesting.
        Supports these formats:
        1. direct arguments
        2. {"arguments": {...}}
        3. {"name": "list_core_networks", "arguments": {...}}
        4. Merged kwargs
        """
        if arguments is None:
            arguments = {}

        # First, extract from nested structures
        if "name" in arguments and "arguments" in arguments:
            arguments = arguments["arguments"]
        
        # Handle deeply nested arguments
        if "arguments" in arguments:
            # Multiple levels of nesting
            while "arguments" in arguments:
                arguments = arguments["arguments"]

        # Merge with kwargs, giving precedence to arguments
        if kwargs:
            arguments = {**kwargs, **arguments}

        return arguments

    async def execute(self, arguments: Dict[str, Any] = None, **kwargs) -> CallToolResult:
        """Execute Core Network discovery with enhanced validation."""
        try:
            # Normalize arguments
            arguments = self._normalize_arguments(arguments, **kwargs)

            # Set parameters
            global_network_id = arguments.get("global_network_id")
            include_policies = arguments.get("include_policies", True)

            self.logger.info(f"Starting Core Network discovery for global network: {global_network_id or 'all'}")

            # Use CoreNetworksResponse for structured response
            from ...models.network import CoreNetworksResponse

            # Discover core networks
            core_networks_response = CoreNetworksResponse(
                global_network_id=global_network_id or "",
                core_networks=[],
                total_count=0,
                policy_documents={}
            )

            try:
                async with self.aws_manager.client_context("networkmanager", "us-west-2") as nm:
                    # Use standard parameter for list
                    list_params = {}
                    if global_network_id:
                        list_params["GlobalNetworkIds"] = [global_network_id]

                    # List core networks with safe parameter passing
                    response = await nm.list_core_networks(**list_params)

                    for cn in response.get("CoreNetworks", []):
                        # Validate network details
                        core_network_info = CoreNetworkInfo(
                            core_network_id=cn.get("CoreNetworkId"),
                            core_network_arn=cn.get("CoreNetworkArn"),
                            global_network_id=cn.get("GlobalNetworkId", global_network_id),
                            description=cn.get("Description"),
                            state=cn.get("State"),
                            edge_locations=cn.get("EdgeLocations", []),
                            tags={
                                tag["Key"]: tag["Value"] 
                                for tag in cn.get("Tags", []) 
                                if isinstance(tag, dict)
                            }
                        )

                        # Optional policy retrieval
                        policy_doc = None
                        if include_policies and cn.get("PolicyVersionId"):
                            try:
                                policy_response = await nm.get_core_network_policy(
                                    CoreNetworkId=cn["CoreNetworkId"],
                                    PolicyVersionId=cn["PolicyVersionId"]
                                )
                                policy_doc = policy_response.get("CoreNetworkPolicy", {}).get("PolicyDocument")
                                
                                # Safely handle policy document conversion
                                if isinstance(policy_doc, str):
                                    try:
                                        policy_doc = json.loads(policy_doc)
                                    except json.JSONDecodeError:
                                        self.logger.warning(f"Could not parse policy document for {cn['CoreNetworkId']}")
                                        policy_doc = None

                            except Exception as policy_error:
                                self.logger.warning(f"Policy retrieval failed for {cn['CoreNetworkId']}: {policy_error}")

                        # Add network to response
                        core_networks_response.add_core_network(core_network_info, policy_doc)

            except (ParamValidationError, ClientError) as e:
                self.logger.error(f"AWS API error discovering core networks: {e}")
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text", 
                            text=json.dumps({
                                "error": str(e),
                                "status": "failure",
                                "error_type": type(e).__name__
                            }, indent=2)
                        )
                    ],
                    isError=True
                )

            except Exception as e:
                self.logger.error(f"Unexpected error discovering core networks: {e}")
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text", 
                            text=json.dumps({
                                "error": str(e),
                                "status": "failure",
                                "error_type": type(e).__name__
                            }, indent=2)
                        )
                    ],
                    isError=True
                )

            # Return as TextContent
            return CallToolResult(
                content=[
                    TextContent(
                        type="text", 
                        text=core_networks_response.model_dump_json(indent=2)
                    )
                ]
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in core network discovery: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text", 
                        text=json.dumps({
                            "error": str(e),
                            "status": "failure"
                        }, indent=2)
                    )
                ],
                isError=True
            )

class GlobalNetworkDiscoveryTool(BaseMCPTool):
    """Tool for discovering Global Networks across AWS regions."""

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig = None):
        super().__init__(aws_manager, config or CloudWANConfig())
        self._tool_name = "get_global_networks"
        self._description = "Discover all Global Networks across AWS regions with detailed information"

    @property
    def tool_name(self) -> str:
        return self._tool_name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "regions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "AWS regions to search (default: all configured regions)",
                    "default": [],
                },
                "global_network_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific Global Network IDs to retrieve (optional)",
                    "default": [],
                },
                "include_device_counts": {
                    "type": "boolean",
                    "description": "Include counts of devices, sites, and links",
                    "default": True,
                },
                "include_tags": {
                    "type": "boolean",
                    "description": "Include resource tags in response",
                    "default": True,
                },
            },
            "required": [],
        }

    def _normalize_arguments(self, arguments: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Normalize arguments with multiple levels of nesting.
        Supports these formats:
        1. direct arguments
        2. {"arguments": {...}}
        3. {"name": "get_global_networks", "arguments": {...}}
        4. Merged kwargs
        """
        if arguments is None:
            arguments = {}

        # First, extract from nested structures
        if "name" in arguments and "arguments" in arguments:
            arguments = arguments["arguments"]
        
        # Handle deeply nested arguments
        if "arguments" in arguments:
            # Multiple levels of nesting
            while "arguments" in arguments:
                arguments = arguments["arguments"]

        # Merge with kwargs, giving precedence to arguments
        if kwargs:
            arguments = {**kwargs, **arguments}

        return arguments

    async def execute(self, arguments: Dict[str, Any] = None, **kwargs) -> CallToolResult:
        """Execute Global Networks discovery."""
        try:
            # Normalize arguments
            arguments = self._normalize_arguments(arguments, **kwargs)

            # Set default parameters if not provided
            global_network_ids = arguments.get("global_network_ids", [])
            include_device_counts = arguments.get("include_device_counts", True)
            include_tags = arguments.get("include_tags", True)
            regions_searched = arguments.get("regions", ["us-west-2"])

            self.logger.info(f"Starting Global Networks discovery")

            # Discover global networks
            global_networks_response = GlobalNetworksResponse(
                global_networks=[],
                total_count=0,
                regions_searched=regions_searched
            )

            try:
                async with self.aws_manager.client_context("networkmanager", "us-west-2") as nm:
                    # Use standard parameter for list
                    list_params = {}
                    if global_network_ids:
                        list_params["GlobalNetworkIds"] = global_network_ids

                    # Fetch global networks
                    response = await nm.describe_global_networks(**list_params)

                    for gn in response.get('GlobalNetworks', []):
                        global_network_data = GlobalNetworkInfo(
                            global_network_id=gn.get("GlobalNetworkId"),
                            global_network_arn=gn.get("GlobalNetworkArn"),
                            description=gn.get("Description"),
                            state=gn.get("State"),
                            tags={
                                tag["Key"]: tag["Value"] 
                                for tag in gn.get("Tags", []) 
                                if isinstance(tag, dict)
                            } if include_tags else {}
                        )

                        # Optional device counts 
                        if include_device_counts:
                            try:
                                device_counts = await nm.get_devices(
                                    GlobalNetworkId=gn["GlobalNetworkId"],
                                    MaxResults=1
                                )
                                global_network_data.device_count = len(device_counts.get("Devices", []))
                            except Exception as device_error:
                                self.logger.warning(f"Could not retrieve device counts: {device_error}")

                        global_networks_response.add_global_network(global_network_data)

            except (ParamValidationError, ClientError) as e:
                self.logger.error(f"AWS API error discovering global networks: {e}")
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text", 
                            text=json.dumps({
                                "error": str(e),
                                "status": "failure",
                                "error_type": type(e).__name__
                            }, indent=2)
                        )
                    ],
                    isError=True
                )

            except Exception as e:
                self.logger.error(f"Unexpected error discovering global networks: {e}")
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text", 
                            text=json.dumps({
                                "error": str(e),
                                "status": "failure",
                                "error_type": type(e).__name__
                            }, indent=2)
                        )
                    ],
                    isError=True
                )

            # Return as TextContent with explicit TextContent object
            return CallToolResult(
                content=[
                    TextContent(
                        type="text", 
                        text=global_networks_response.model_dump_json(indent=2)
                    )
                ]
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in global networks discovery: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text", 
                        text=json.dumps({
                            "error": str(e),
                            "status": "failure"
                        }, indent=2)
                    )
                ],
                isError=True
            )


class VPCDiscoveryTool(BaseMCPTool):
    """Tool for VPC discovery and analysis."""

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig = None):
        super().__init__(aws_manager, config or CloudWANConfig())
        self._tool_name = "discover_vpcs"
        self._description = "Discover VPCs across AWS regions with CloudWAN context"

    @property
    def tool_name(self) -> str:
        return self._tool_name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "regions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "AWS regions to search (default: all configured regions)",
                    "default": [],
                },
                "include_attachments": {
                    "type": "boolean",
                    "description": "Include CloudWAN attachment information",
                    "default": True,
                },
            },
            "required": [],
        }

    def _normalize_arguments(self, arguments: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Normalize arguments with multiple levels of nesting."""
        if arguments is None:
            arguments = {}

        if "arguments" in arguments:
            while "arguments" in arguments:
                arguments = arguments["arguments"]

        if kwargs:
            arguments = {**kwargs, **arguments}

        return arguments

    async def execute(self, arguments: Dict[str, Any] = None, **kwargs) -> CallToolResult:
        """Execute VPC discovery."""
        try:
            arguments = self._normalize_arguments(arguments, **kwargs)
            regions = arguments.get("regions", ["us-west-2"])
            
            self.logger.info(f"Starting VPC discovery for regions: {regions}")

            from ...models.network import VPCDiscoveryResponse, VPCInfo

            vpcs_response = VPCDiscoveryResponse(
                vpcs=[],
                total_count=0,
                regions_searched=regions,
                cloudwan_attachments=[]
            )

            try:
                for region in regions:
                    async with self.aws_manager.client_context("ec2", region) as ec2:
                        response = await ec2.describe_vpcs()
                        
                        for vpc in response.get("Vpcs", []):
                            vpc_info = VPCInfo(
                                vpc_id=vpc.get("VpcId"),
                                region=region,
                                cidr_block=vpc.get("CidrBlock"),
                                state=vpc.get("State"),
                                is_default=vpc.get("IsDefault", False),
                                tags={
                                    tag["Key"]: tag["Value"]
                                    for tag in vpc.get("Tags", [])
                                    if isinstance(tag, dict)
                                }
                            )
                            vpcs_response.add_vpc(vpc_info)

            except Exception as e:
                self.logger.error(f"VPC discovery failed: {e}")
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps({
                                "error": str(e),
                                "status": "failure",
                                "regions_searched": regions
                            }, indent=2)
                        )
                    ],
                    isError=True
                )

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=vpcs_response.model_dump_json(indent=2)
                    )
                ]
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in VPC discovery: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "error": str(e),
                            "status": "failure"
                        }, indent=2)
                    )
                ],
                isError=True
            )


class IPDetailsDiscoveryTool(BaseMCPTool):
    """Tool for IP address details discovery and analysis."""

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig = None):
        super().__init__(aws_manager, config or CloudWANConfig())
        self._tool_name = "discover_ip_details"
        self._description = "Discover detailed information about IP addresses and their network context"

    @property
    def tool_name(self) -> str:
        return self._tool_name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ip_address": {
                    "type": "string",
                    "description": "IP address to analyze",
                },
                "include_security_groups": {
                    "type": "boolean",
                    "description": "Include security group information",
                    "default": True,
                },
            },
            "required": ["ip_address"],
        }

    def _normalize_arguments(self, arguments: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Normalize arguments with multiple levels of nesting."""
        if arguments is None:
            arguments = {}

        if "arguments" in arguments:
            while "arguments" in arguments:
                arguments = arguments["arguments"]

        if kwargs:
            arguments = {**kwargs, **arguments}

        return arguments

    async def execute(self, arguments: Dict[str, Any] = None, **kwargs) -> CallToolResult:
        """Execute IP details discovery."""
        try:
            arguments = self._normalize_arguments(arguments, **kwargs)
            ip_address = arguments.get("ip_address")
            
            if not ip_address:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps({
                                "error": "ip_address parameter is required",
                                "status": "failure"
                            }, indent=2)
                        )
                    ],
                    isError=True
                )

            self.logger.info(f"Starting IP details discovery for: {ip_address}")

            from ...models.network import IPDetailsResponse

            ip_response = IPDetailsResponse(
                ip_address=ip_address,
                context=None,
                security_groups=[],
                route_tables=[],
                cloudwan_segment=None,
                is_segment_isolated=False,
                dns_resolution=None
            )

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=ip_response.model_dump_json(indent=2)
                    )
                ]
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in IP details discovery: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "error": str(e),
                            "status": "failure"
                        }, indent=2)
                    )
                ],
                isError=True
            )