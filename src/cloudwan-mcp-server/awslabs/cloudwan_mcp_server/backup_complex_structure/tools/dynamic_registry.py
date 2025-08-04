"""
Dynamic Tool Registry for CloudWAN MCP Server.

This module implements a hybrid tiered loading system with factory pattern
for dynamic tool loading, addressing the server startup bottleneck.
"""
import asyncio
import importlib
import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from mcp.server import Server
from mcp.types import CallToolResult, TextContent, ErrorData
from mcp import McpError
import json

logger = logging.getLogger(__name__)


class ToolTier(Enum):
    CORE = "core"
    EXTENDED = "extended"
    PREMIUM = "premium"


@dataclass
class ToolMetadata:
    name: str
    module_path: str
    class_name: str
    tier: ToolTier
    description: str
    inputSchema: Optional[dict] = None
    outputSchema: Optional[dict] = None
    dependencies: Optional[List[str]] = None
    priority: int = 5
    estimated_load_time: float = 0.5
    requires_aws: bool = True

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        self.inputSchema = self.inputSchema or {
            "type": "object",
            "properties": {"arguments": {"type": "object", "additionalProperties": True}},
            "additionalProperties": False
        }
        self.outputSchema = self.outputSchema or {
            "type": "object",
            "properties": {
                "content": {
                    "type": "array",
                    "items": {"type": "object", "required": ["type", "text"]}
                }
            },
            "required": ["content"]
        }


class SchemaValidator:
    @classmethod
    def validate_tool_registration(cls, metadata: ToolMetadata) -> None:
        if not metadata.inputSchema:
            error_data = ErrorData(code=-32602, message=f"Missing inputSchema: {metadata.name}")
            raise McpError(error_data)
        if not metadata.outputSchema:
            error_data = ErrorData(code=-32602, message=f"Missing outputSchema: {metadata.name}")
            raise McpError(error_data)
        cls._validate_json_schema(metadata.inputSchema, f"{metadata.name} input")
        cls._validate_json_schema(metadata.outputSchema, f"{metadata.name} output")

    @staticmethod
    def _validate_json_schema(schema: dict, context: str) -> None:
        if not schema.get("type"):
            error_data = ErrorData(code=-32602, message=f"Schema missing type: {context}")
            raise McpError(error_data)
        if schema["type"] != "object":
            error_data = ErrorData(code=-32602, message=f"Root type must be object: {context}")
            raise McpError(error_data)
        # Properties are optional - allow schemas without properties


class ToolFactory:
    def __init__(self, aws_manager, config):
        self.aws_manager = aws_manager
        self.config = config
        self.cache: Dict[str, Any] = {}
        self.loading_locks: Dict[str, asyncio.Lock] = {}
        self.load_stats: Dict[str, float] = {}
        self.load_errors: Dict[str, str] = {}  # Track load errors for debugging
        # Increased worker count and optimized for I/O bound operations
        self._executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="tool-loader")

    async def create_tool(self, metadata: ToolMetadata, force_reload=False) -> Any:
        if not force_reload and metadata.name in self.cache:
            return self.cache[metadata.name]

        if metadata.name not in self.loading_locks:
            self.loading_locks[metadata.name] = asyncio.Lock()

        async with self.loading_locks[metadata.name]:
            # Double-check pattern for thread safety
            if not force_reload and metadata.name in self.cache:
                return self.cache[metadata.name]

            logger.info(f"Loading tool: {metadata.name} (tier: {metadata.tier.value})")
            start = time.time()
            try:
                # Load tool in thread pool to avoid blocking event loop
                loop = asyncio.get_event_loop()
                instance = await loop.run_in_executor(
                    self._executor,
                    self._load_tool_sync,
                    metadata
                )
                
                self.cache[metadata.name] = instance
                load_time = time.time() - start
                self.load_stats[metadata.name] = load_time
                
                # Clear any previous errors
                self.load_errors.pop(metadata.name, None)
                
                logger.debug(f"Successfully loaded {metadata.name} in {load_time:.3f}s")
                return instance
                
            except Exception as e:
                load_time = time.time() - start
                error_msg = f"Tool load failed after {load_time:.3f}s: {str(e)}"
                
                logger.error(f"Load failed: {metadata.name} - {error_msg}")
                self.load_errors[metadata.name] = error_msg
                
                error_data = ErrorData(
                    code=-32603, 
                    message=f"Tool load failed: {metadata.name}",
                    data={"error": error_msg, "load_time": load_time}
                )
                raise McpError(error_data)

    def _load_tool_sync(self, metadata: ToolMetadata) -> Any:
        try:
            module = importlib.import_module(metadata.module_path)
            tool_class = getattr(module, metadata.class_name)
            args = [self.aws_manager, self.config] if metadata.requires_aws else [self.config]
            instance = tool_class(*args)
            instance.execute = self._create_validated_execute(
                instance.execute, metadata.inputSchema, metadata.outputSchema
            )
            return instance
        except Exception as e:
            logger.error(f"Error: {metadata.name} - {e}")
            raise

    def _create_validated_execute(self, func, input_schema, output_schema):
        async def wrapper(arguments: Dict[str, Any]) -> CallToolResult:
            try:
                from jsonschema import validate
                if input_schema:
                    validate(instance=arguments, schema=input_schema)
            except Exception as e:
                error_data = ErrorData(code=-32602, message=f"Validation error: {e}")
                raise McpError(error_data)
            
            try:
                result = await func(arguments)
                
                # Ensure result is CallToolResult format
                if isinstance(result, CallToolResult):
                    return result
                elif isinstance(result, list) and all(hasattr(item, 'type') and hasattr(item, 'text') for item in result):
                    return CallToolResult(content=result)
                elif isinstance(result, dict):
                    import json
                    return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])
                elif isinstance(result, str):
                    return CallToolResult(content=[TextContent(type="text", text=result)])
                else:
                    return CallToolResult(content=[TextContent(type="text", text=str(result))])
                    
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                error_data = ErrorData(code=-32603, message=f"Execution error: {e}")
                raise McpError(error_data)
        return wrapper

    def get_load_statistics(self) -> Dict[str, Any]:
        total_load_time = sum(self.load_stats.values()) if self.load_stats else 0
        return {
            "loaded_tools": len(self.cache),
            "failed_tools": len(self.load_errors),
            "load_stats": self.load_stats,
            "load_errors": self.load_errors,
            "total_load_time": total_load_time,
            "avg_load_time": total_load_time / len(self.load_stats) if self.load_stats else 0,
            "fastest_tool": min(self.load_stats.items(), key=lambda x: x[1])[0] if self.load_stats else None,
            "slowest_tool": max(self.load_stats.items(), key=lambda x: x[1])[0] if self.load_stats else None
        }


class DynamicToolRegistry:
    def __init__(self, aws_manager, config):
        self.factory = ToolFactory(aws_manager, config)
        self.tools: Dict[str, ToolMetadata] = {}
        self.tiers: Dict[ToolTier, List[str]] = {t: [] for t in ToolTier}
        self.loaded: Set[str] = set()
        self.failed: Set[str] = set()

    def register_tool(self, metadata: ToolMetadata) -> None:
        try:
            SchemaValidator.validate_tool_registration(metadata)
            self.tools[metadata.name] = metadata
            self.tiers[metadata.tier].append(metadata.name)
        except McpError as e:
            logger.error(f"Registration failed: {metadata.name} - {e}")
            self.failed.add(metadata.name)

    async def load_core_tools(self) -> Dict[str, Any]:
        """Load core tier tools with optimized concurrency and error handling."""
        core_tools = [self.tools[name] for name in self.tiers[ToolTier.CORE]]
        
        if not core_tools:
            logger.warning("No core tools defined")
            return {}
        
        logger.info(f"Loading {len(core_tools)} core tools concurrently...")
        start_time = time.time()
        
        # Create tasks with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(4)  # Limit to 4 concurrent loads
        
        async def load_with_semaphore(tool_metadata):
            async with semaphore:
                return await self.factory.create_tool(tool_metadata)
        
        tasks = [load_with_semaphore(tool) for tool in core_tools]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        loaded = {}
        failed = []
        
        for tool, result in zip(core_tools, results):
            if isinstance(result, Exception):
                logger.error(f"Core tool {tool.name} failed to load: {result}")
                failed.append(tool.name)
                self.failed.add(tool.name)
            else:
                loaded[tool.name] = result
                self.loaded.add(tool.name)
        
        load_time = time.time() - start_time
        logger.info(f"Core tools loaded: {len(loaded)}/{len(core_tools)} in {load_time:.2f}s")
        
        if failed:
            logger.warning(f"Failed core tools: {', '.join(failed)}")
            
        return loaded

    async def load_extended_tools(self) -> Dict[str, Any]:
        """Load extended tier tools with batched loading for better performance."""
        extended_tools = [self.tools[name] for name in self.tiers[ToolTier.EXTENDED]]
        
        if not extended_tools:
            logger.info("No extended tools to load")
            return {}
            
        logger.info(f"Loading {len(extended_tools)} extended tools...")
        start_time = time.time()
        
        # Sort by estimated load time for optimal batching
        extended_tools.sort(key=lambda t: t.estimated_load_time)
        
        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(3)  # Slightly lower for extended tools
        
        async def load_with_semaphore(tool_metadata):
            async with semaphore:
                return await self.factory.create_tool(tool_metadata)
        
        tasks = [load_with_semaphore(tool) for tool in extended_tools]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        loaded = {}
        failed = []
        
        for tool, result in zip(extended_tools, results):
            if isinstance(result, Exception):
                logger.warning(f"Extended tool {tool.name} failed to load: {result}")
                failed.append(tool.name)
                self.failed.add(tool.name)
            else:
                loaded[tool.name] = result
                self.loaded.add(tool.name)
        
        load_time = time.time() - start_time
        logger.info(f"Extended tools loaded: {len(loaded)}/{len(extended_tools)} in {load_time:.2f}s")
        
        if failed:
            logger.info(f"Failed extended tools (non-critical): {', '.join(failed)}")
            
        return loaded

    async def load_all_tools(self) -> Dict[str, Any]:
        """Load all tools in priority order."""
        all_loaded = {}
        
        # Load core tools first
        core_loaded = await self.load_core_tools()
        all_loaded.update(core_loaded)
        
        # Load extended tools
        extended_loaded = await self.load_extended_tools()
        all_loaded.update(extended_loaded)
        
        return all_loaded

    async def get_tool(self, name: str) -> Optional[Any]:
        """Get a tool instance by name, loading it if necessary."""
        if name not in self.tools:
            logger.error(f"Tool '{name}' not found in registry")
            return None
        
        tool_metadata = self.tools[name]
        
        try:
            # Create the tool instance using the factory
            tool_instance = await self.factory.create_tool(tool_metadata)
            if tool_instance:
                self.loaded.add(name)
                logger.info(f"Successfully loaded tool: {name}")
            else:
                self.failed.add(name)
                logger.error(f"Failed to create tool instance: {name}")
            return tool_instance
        except Exception as e:
            logger.error(f"Error loading tool '{name}': {e}")
            self.failed.add(name)
            return None

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics for monitoring and logging."""
        return {
            "total_tools": len(self.tools),
            "tools_by_tier": {
                tier.value: len(tool_names) 
                for tier, tool_names in self.tiers.items()
            },
            "loaded_tools": len(self.loaded),
            "failed_tools": len(self.failed),
            "load_success_rate": len(self.loaded) / len(self.tools) if self.tools else 0,
            "factory_stats": self.factory.get_load_statistics(),
        }


DYNAMIC_TOOL_DEFINITIONS = [
    # Core Tools - Load Immediately
    ToolMetadata(
        name="trace_network_path",
        module_path="awslabs.cloudwan_mcp_server.tools.core.path_tracing",
        class_name="NetworkPathTracingTool",
        tier=ToolTier.CORE,
        description="Trace network paths between IPs",
        inputSchema={
            "type": "object",
            "properties": {
                "source_ip": {"type": "string", "pattern": r"^\d{1,3}(\.\d{1,3}){3}$"},
                "destination_ip": {"type": "string", "pattern": r"^\d{1,3}(\.\d{1,3}){3}$"},
                "region": {"type": "string", "default": "us-east-1"},
                "include_intermediate_hops": {"type": "boolean", "default": True},
                "trace_mode": {
                    "type": "string",
                    "enum": ["vpc-reachability", "transit-gateway", "both"],
                    "default": "both"
                }
            },
            "required": ["source_ip", "destination_ip"],
            "additionalProperties": False
        },
        outputSchema={
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "trace_results": {"type": "array"},
                "total_hops": {"type": "integer"},
                "path_status": {"type": "string"},
                "errors": {"type": "array"}
            },
            "required": ["success"]
        },
        priority=1,
        estimated_load_time=0.3
    ),
    ToolMetadata(
        name="list_core_networks",
        module_path="awslabs.cloudwan_mcp_server.tools.core.discovery",
        class_name="CoreNetworkDiscoveryTool",
        tier=ToolTier.CORE,
        description="List CloudWAN core networks",
        inputSchema={"type": "object"},
        outputSchema={
            "type": "object",
            "properties": {"core_networks": {"type": "array"}},
            "required": ["core_networks"]
        },
        priority=1,
        estimated_load_time=0.2
    ),
    ToolMetadata(
        name="get_global_networks",
        module_path="awslabs.cloudwan_mcp_server.tools.core.discovery",
        class_name="GlobalNetworkDiscoveryTool",
        tier=ToolTier.CORE,
        description="Discover global networks",
        inputSchema={"type": "object"},
        outputSchema={
            "type": "object",
            "properties": {"success": {"type": "boolean"}, "global_networks": {"type": "array"}},
            "required": ["success"]
        },
        priority=1,
        estimated_load_time=0.2
    ),
    ToolMetadata(
        name="discover_vpcs",
        module_path="awslabs.cloudwan_mcp_server.tools.core.discovery",
        class_name="VPCDiscoveryTool",
        tier=ToolTier.CORE,
        description="Discover VPCs",
        inputSchema={"type": "object"},
        outputSchema={
            "type": "object",
            "properties": {"vpcs": {"type": "array"}},
            "required": ["vpcs"]
        },
        priority=1,
        estimated_load_time=0.4
    ),
    ToolMetadata(
        name="discover_ip_details",
        module_path="awslabs.cloudwan_mcp_server.tools.core.discovery",
        class_name="IPDetailsDiscoveryTool",
        tier=ToolTier.CORE,
        description="IP details discovery",
        inputSchema={"type": "object"},
        outputSchema={
            "type": "object",
            "properties": {"ip_address": {"type": "string"}, "success": {"type": "boolean"}},
            "required": ["ip_address", "success"]
        },
        priority=1,
        estimated_load_time=0.2
    ),
    # Extended tier tools
    ToolMetadata(
        name="validate_ip_cidr",
        module_path="awslabs.cloudwan_mcp_server.tools.validation.ip_cidr_validator_tool",
        class_name="IPCIDRValidatorTool",
        tier=ToolTier.EXTENDED,
        description="Comprehensive IP/CIDR validation and networking utilities",
        inputSchema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["validate_ip", "validate_cidr", "calculate_subnets", "generate_subnets", "check_overlap", "ip_range_to_cidrs", "cidr_to_ip_range", "comprehensive_analysis"],
                    "description": "Type of networking operation to perform"
                },
                "ip": {"type": "string", "description": "IP address for validation"},
                "cidr": {"type": "string", "description": "CIDR block for validation/analysis"},
                "networks": {"type": "array", "items": {"type": "string"}, "description": "List of networks for overlap analysis"}
            },
            "required": ["operation"]
        },
        outputSchema={
            "type": "object",
            "properties": {
                "operation": {"type": "string"},
                "success": {"type": "boolean"},
                "result": {"type": "object"}
            }
        },
        requires_aws=False,
        priority=2,
        estimated_load_time=0.1
    ),
    ToolMetadata(
        name="list_network_function_groups",
        module_path="awslabs.cloudwan_mcp_server.tools.cloudwan.network_function_groups",
        class_name="ListNetworkFunctionGroupsTool",
        tier=ToolTier.EXTENDED,
        description="List and discover Network Function Groups",
        inputSchema={"type": "object"},
        outputSchema={
            "type": "object",
            "properties": {"network_function_groups": {"type": "array"}},
            "required": ["network_function_groups"]
        },
        priority=2,
        estimated_load_time=0.4
    ),
    ToolMetadata(
        name="analyze_network_function_group",
        module_path="awslabs.cloudwan_mcp_server.tools.cloudwan.network_function_groups",
        class_name="AnalyzeNetworkFunctionGroupPoliciesTool",
        tier=ToolTier.EXTENDED,
        description="Analyze Network Function Group details and policies",
        inputSchema={"type": "object"},
        outputSchema={
            "type": "object",
            "properties": {"policy_analysis": {"type": "array"}},
            "required": ["policy_analysis"]
        },
        priority=2,
        estimated_load_time=0.5
    ),
    ToolMetadata(
        name="validate_cloudwan_policy",
        module_path="awslabs.cloudwan_mcp_server.tools.intelligence.policy_validator",
        class_name="PolicyValidatorTool",
        tier=ToolTier.EXTENDED,
        description="Validate CloudWAN policy configurations",
        inputSchema={"type": "object"},
        outputSchema={
            "type": "object",
            "properties": {"validation_results": {"type": "array"}},
            "required": ["validation_results"]
        },
        priority=2,
        estimated_load_time=0.3
    ),
    ToolMetadata(
        name="manage_tgw_routes",
        module_path="awslabs.cloudwan_mcp_server.tools.core.tgw_routes",
        class_name="TransitGatewayRoutesTool",
        tier=ToolTier.EXTENDED,
        description="Manage Transit Gateway routes - list, create, delete, blackhole",
        inputSchema={"type": "object"},
        outputSchema={
            "type": "object",
            "properties": {"route_operation_result": {"type": "object"}},
            "required": ["route_operation_result"]
        },
        priority=2,
        estimated_load_time=0.4
    ),
    # Phase 1 High-Value Tools - Production Ready
    ToolMetadata(
        name="analyze_tgw_routes",
        module_path="awslabs.cloudwan_mcp_server.tools.core.tgw_route_analyzer",
        class_name="TGWRouteAnalyzer",
        tier=ToolTier.CORE,
        description="Comprehensive Transit Gateway route analysis - overlaps, blackholes, cross-region",
        inputSchema={"type": "object"},
        outputSchema={
            "type": "object",
            "properties": {"route_analysis": {"type": "object"}},
            "required": ["route_analysis"]
        },
        priority=1,
        estimated_load_time=0.5
    ),
    ToolMetadata(
        name="analyze_tgw_peers",
        module_path="awslabs.cloudwan_mcp_server.tools.core.tgw_peer_analyzer",
        class_name="TGWPeerAnalyzer",
        tier=ToolTier.CORE,
        description="Transit Gateway peering analysis and troubleshooting",
        inputSchema={"type": "object"},
        outputSchema={
            "type": "object",
            "properties": {"peer_analysis": {"type": "object"}},
            "required": ["peer_analysis"]
        },
        priority=1,
        estimated_load_time=0.4
    ),
    ToolMetadata(
        name="analyze_segment_routes",
        module_path="awslabs.cloudwan_mcp_server.tools.core.segment_route_analyzer",
        class_name="SegmentRouteAnalyzer",
        tier=ToolTier.EXTENDED,
        description="CloudWAN segment routing analysis and optimization",
        inputSchema={"type": "object"},
        outputSchema={
            "type": "object",
            "properties": {"segment_analysis": {"type": "object"}},
            "required": ["segment_analysis"]
        },
        priority=2,
        estimated_load_time=0.4
    ),

    # CloudWAN Policy Management Tools
    ToolMetadata(
        name="get_core_network_policy",
        module_path="awslabs.cloudwan_mcp_server.tools.cloudwan.policy_management",
        class_name="GetCoreNetworkPolicyTool",
        tier=ToolTier.CORE,
        description="Retrieve the policy document for a CloudWAN Core Network",
        inputSchema={
            "type": "object",
            "properties": {
                "core_network_id": {"type": "string"},
                "policy_version_id": {"type": "string"},
                "alias": {"type": "string", "enum": ["LIVE", "LATEST"]}
            },
            "required": ["core_network_id"]
        },
        outputSchema={
            "type": "object",
            "properties": {
                "core_network_id": {"type": "string"},
                "policy_document": {"type": "object"}
            },
            "required": ["core_network_id"]
        },
        priority=1,
        estimated_load_time=0.2
    ),
    
    ToolMetadata(
        name="get_core_network_change_set",
        module_path="awslabs.cloudwan_mcp_server.tools.cloudwan.policy_management", 
        class_name="GetCoreNetworkChangeSetTool",
        tier=ToolTier.CORE,
        description="Retrieve policy change sets for a CloudWAN Core Network",
        inputSchema={
            "type": "object",
            "properties": {
                "core_network_id": {"type": "string"},
                "policy_version_id": {"type": "string"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
                "next_token": {"type": "string"}
            },
            "required": ["core_network_id", "policy_version_id"]
        },
        outputSchema={
            "type": "object",
            "properties": {
                "core_network_id": {"type": "string"},
                "change_sets": {"type": "array"}
            },
            "required": ["core_network_id", "change_sets"]
        },
        priority=1,
        estimated_load_time=0.3
    ),
    
    ToolMetadata(
        name="get_core_network_change_events",
        module_path="awslabs.cloudwan_mcp_server.tools.cloudwan.policy_management",
        class_name="GetCoreNetworkChangeEventsTool", 
        tier=ToolTier.CORE,
        description="Retrieve change events for a CloudWAN Core Network",
        inputSchema={
            "type": "object",
            "properties": {
                "core_network_id": {"type": "string"},
                "policy_version_id": {"type": "string"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
                "next_token": {"type": "string"}
            },
            "required": ["core_network_id", "policy_version_id"]
        },
        outputSchema={
            "type": "object", 
            "properties": {
                "core_network_id": {"type": "string"},
                "change_events": {"type": "array"}
            },
            "required": ["core_network_id", "change_events"]
        },
        priority=1,
        estimated_load_time=0.3
    ),

    # Premium tier tools - advanced analysis (temporarily disabled due to import issues)
    # ToolMetadata(
    #     name="analyze_bgp_protocol", 
    #     module_path="awslabs.cloudwan_mcp_server.tools.networking.bgp_protocol_analyzer",
    #     class_name="BGPProtocolAnalyzer",
    #     tier=ToolTier.PREMIUM,
    #     description="Advanced BGP protocol analysis and troubleshooting",
    #     inputSchema={"type": "object"},
    #     outputSchema={"type": "object"},
    #     priority=3,
    #     estimated_load_time=0.8
    # )
]


async def register_dynamic_tools(server: Server, aws_manager, config) -> DynamicToolRegistry:
    registry = DynamicToolRegistry(aws_manager, config)
    for tool in DYNAMIC_TOOL_DEFINITIONS:
        registry.register_tool(tool)
    
    # Load core and extended tools
    loaded_tools = await registry.load_all_tools()
    
    logger.info(f"Initialized: {len(registry.tools)} total tools, {len(loaded_tools)} loaded successfully")
    logger.info(f"Tool breakdown - Core: {len(registry.tiers[ToolTier.CORE])}, Extended: {len(registry.tiers[ToolTier.EXTENDED])}, Premium: {len(registry.tiers[ToolTier.PREMIUM])}")
    
    return registry