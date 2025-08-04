"""
CloudWAN Professional Diagrams MCP Tool.

This tool provides MCP server integration for generating professional CloudWAN network diagrams
using the advanced diagram rendering system and AWS Diagram MCP server integration.
"""

from typing import Dict, List, Any
from pathlib import Path

from mcp.server import Server
from mcp.types import Tool, TextContent

from .base import BaseTool, ToolError
from .visualization.cloudwan_diagram_suite import (
    CloudWANDiagramSuite,
    DiagramSuiteConfiguration,
    generate_executive_diagram_suite,
    generate_technical_diagram_suite,
    generate_operational_diagram_suite,
)
from .visualization.advanced_diagram_renderer import (
    DiagramFormat,
    DiagramStyle,
    LayoutStrategy,
    DiagramConfiguration,
)
from ..aws.client_manager import AWSClientManager
from ..config import CloudWANConfig


class CloudWANProfessionalDiagramsTool(BaseTool):
    """
    Professional CloudWAN diagram generation tool.

    Provides comprehensive diagram generation capabilities including:
    - Three-pane professional layouts
    - Multiple output formats (PNG, SVG, HTML, JSON, Mermaid)
    - Specialized visualizations (NFG flows, TGW peering, segment routing)
    - Executive, technical, and operational diagram suites
    - AWS Diagram MCP server integration for high-quality rendering
    """

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        super().__init__("CloudWAN Professional Diagrams", aws_manager, config)
        self.diagram_suite = CloudWANDiagramSuite(aws_manager, config)

    def get_tools(self) -> List[Tool]:
        """Return list of available MCP tools."""
        return [
            Tool(
                name="generate_cloudwan_three_pane_diagram",
                description=(
                    "Generate professional three-pane CloudWAN diagram showing Core Network A "
                    "(Production/NonProduction), Core Network B (CrossOrg), and Inspection & TGW Peering. "
                    "This is the flagship visualization for CloudWAN architectures."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "regions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "AWS regions to analyze (optional, defaults to configured regions)",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Output path for diagram file (optional, auto-generated if not provided)",
                        },
                        "workspace_dir": {
                            "type": "string",
                            "description": "Workspace directory for saving diagrams (optional, defaults to current directory)",
                        },
                        "format": {
                            "type": "string",
                            "enum": [
                                "png",
                                "svg",
                                "html",
                                "json",
                                "mermaid",
                                "python_code",
                            ],
                            "description": "Output format for the diagram (default: png)",
                        },
                        "style": {
                            "type": "string",
                            "enum": [
                                "professional",
                                "corporate",
                                "technical",
                                "minimalist",
                                "colorful",
                            ],
                            "description": "Visual styling for the diagram (default: professional)",
                        },
                        "show_details": {
                            "type": "boolean",
                            "description": "Include detailed labels and connection information (default: true)",
                        },
                        "high_resolution": {
                            "type": "boolean",
                            "description": "Generate high-resolution diagram (default: true)",
                        },
                    },
                },
            ),
            Tool(
                name="generate_cloudwan_nfg_inspection_diagram",
                description=(
                    "Generate Network Function Group (NFG) inspection flow diagram showing "
                    "send-to/send-via targets, inspection routing, and network function flows."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "regions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "AWS regions to analyze",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Output path for diagram file",
                        },
                        "workspace_dir": {
                            "type": "string",
                            "description": "Workspace directory for saving diagrams",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["png", "svg", "html", "json", "mermaid"],
                            "description": "Output format (default: png)",
                        },
                    },
                },
            ),
            Tool(
                name="generate_cloudwan_tgw_peering_diagram",
                description=(
                    "Generate Transit Gateway peering analysis diagram showing TGW peering connections, "
                    "cross-account routing, and peering chain relationships."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "regions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "AWS regions to analyze",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Output path for diagram file",
                        },
                        "workspace_dir": {
                            "type": "string",
                            "description": "Workspace directory for saving diagrams",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["png", "svg", "html", "json", "mermaid"],
                            "description": "Output format (default: png)",
                        },
                    },
                },
            ),
            Tool(
                name="generate_cloudwan_segment_routing_diagram",
                description=(
                    "Generate CloudWAN segment routing flow diagram showing segment policies, "
                    "routing decisions, and inter-segment traffic flows."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "regions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "AWS regions to analyze",
                        },
                        "segment_filter": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific segments to include in the diagram",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Output path for diagram file",
                        },
                        "workspace_dir": {
                            "type": "string",
                            "description": "Workspace directory for saving diagrams",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["png", "svg", "html", "json", "mermaid"],
                            "description": "Output format (default: png)",
                        },
                    },
                },
            ),
            Tool(
                name="generate_cloudwan_diagram_suite",
                description=(
                    "Generate comprehensive CloudWAN diagram suite with multiple visualization strategies. "
                    "Includes executive overview, technical deep-dive, and operational dashboard sets."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "suite_type": {
                            "type": "string",
                            "enum": [
                                "executive",
                                "technical",
                                "operational",
                                "troubleshooting",
                            ],
                            "description": "Type of diagram suite to generate (default: technical)",
                        },
                        "output_directory": {
                            "type": "string",
                            "description": "Output directory for diagram suite (default: cloudwan_diagrams)",
                        },
                        "regions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "AWS regions to analyze",
                        },
                        "workspace_dir": {
                            "type": "string",
                            "description": "Workspace directory for saving diagrams",
                        },
                        "high_resolution": {
                            "type": "boolean",
                            "description": "Generate high-resolution diagrams (default: true)",
                        },
                        "include_interactive": {
                            "type": "boolean",
                            "description": "Include interactive HTML diagrams (default: true)",
                        },
                        "max_elements": {
                            "type": "integer",
                            "description": "Maximum elements per diagram for readability (default: 50)",
                        },
                        "generate_all_formats": {
                            "type": "boolean",
                            "description": "Generate multiple output formats (default: false)",
                        },
                    },
                },
            ),
            Tool(
                name="generate_cloudwan_custom_diagram",
                description=(
                    "Generate custom CloudWAN diagram with specific layout strategy, style, and configuration. "
                    "Provides full control over diagram generation parameters."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "layout_strategy": {
                            "type": "string",
                            "enum": [
                                "three_pane",
                                "hierarchical_flow",
                                "segment_focused",
                                "regional_clusters",
                                "nfg_inspection",
                                "tgw_peering",
                            ],
                            "description": "Layout strategy for organizing elements (default: three_pane)",
                        },
                        "style": {
                            "type": "string",
                            "enum": [
                                "professional",
                                "corporate",
                                "technical",
                                "minimalist",
                                "colorful",
                            ],
                            "description": "Visual styling (default: professional)",
                        },
                        "format": {
                            "type": "string",
                            "enum": [
                                "png",
                                "svg",
                                "html",
                                "json",
                                "mermaid",
                                "python_code",
                            ],
                            "description": "Output format (default: png)",
                        },
                        "regions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "AWS regions to analyze",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Output path for diagram file",
                        },
                        "workspace_dir": {
                            "type": "string",
                            "description": "Workspace directory for saving diagrams",
                        },
                        "show_labels": {
                            "type": "boolean",
                            "description": "Show element labels (default: true)",
                        },
                        "show_cidr_blocks": {
                            "type": "boolean",
                            "description": "Show CIDR block information (default: true)",
                        },
                        "show_connection_details": {
                            "type": "boolean",
                            "description": "Show detailed connection information (default: true)",
                        },
                        "group_by_region": {
                            "type": "boolean",
                            "description": "Group elements by AWS region (default: true)",
                        },
                        "group_by_segment": {
                            "type": "boolean",
                            "description": "Group elements by CloudWAN segment (default: true)",
                        },
                        "max_elements": {
                            "type": "integer",
                            "description": "Maximum elements per group (default: 20)",
                        },
                        "width": {
                            "type": "integer",
                            "description": "Diagram width in pixels (default: 1600)",
                        },
                        "height": {
                            "type": "integer",
                            "description": "Diagram height in pixels (default: 1200)",
                        },
                    },
                },
            ),
        ]

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute the specified tool with given arguments."""

        try:
            if name == "generate_cloudwan_three_pane_diagram":
                return await self._generate_three_pane_diagram(arguments)
            elif name == "generate_cloudwan_nfg_inspection_diagram":
                return await self._generate_nfg_inspection_diagram(arguments)
            elif name == "generate_cloudwan_tgw_peering_diagram":
                return await self._generate_tgw_peering_diagram(arguments)
            elif name == "generate_cloudwan_segment_routing_diagram":
                return await self._generate_segment_routing_diagram(arguments)
            elif name == "generate_cloudwan_diagram_suite":
                return await self._generate_diagram_suite(arguments)
            elif name == "generate_cloudwan_custom_diagram":
                return await self._generate_custom_diagram(arguments)
            else:
                raise ToolError(f"Unknown tool: {name}")

        except Exception as e:
            self.logger.error(f"Tool execution failed for {name}: {e}")
            raise ToolError(f"Tool execution failed: {str(e)}")

    async def _generate_three_pane_diagram(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Generate professional three-pane CloudWAN diagram."""

        try:
            regions = arguments.get("regions")
            output_path = arguments.get("output_path")
            workspace_dir = arguments.get("workspace_dir", str(Path.cwd()))
            diagram_format = arguments.get("format", "png")
            style = arguments.get("style", "professional")
            show_details = arguments.get("show_details", True)
            high_resolution = arguments.get("high_resolution", True)

            self.logger.info("Generating three-pane CloudWAN diagram")

            # Generate the diagram
            result = await self.diagram_suite.generate_three_pane_professional(
                regions=regions, output_path=output_path, workspace_dir=workspace_dir
            )

            if result.success:
                response_lines = [
                    "✅ **CloudWAN Three-Pane Professional Diagram Generated Successfully!**",
                    "",
                    "📊 **Network Analysis:**",
                    f"   • Elements Analyzed: {result.element_count}",
                    f"   • Connections Mapped: {result.connection_count}",
                    f"   • Generation Time: {result.generation_time:.2f}s",
                    "",
                    "🎨 **Diagram Features:**",
                    "   • Layout: Three-Pane Professional (Core Network A | Core Network B | Inspection & TGW)",
                    f"   • Style: {style.title()}",
                    f"   • Format: {diagram_format.upper()}",
                    f"   • Resolution: {'High (1800x1200)' if high_resolution else 'Standard (1200x800)'}",
                    "",
                    "📁 **Generated Files:**",
                ]

                for format_type, path in result.diagram_paths.items():
                    if path:
                        filename = Path(path).name
                        response_lines.append(f"   • {format_type.upper()}: `{filename}`")
                        response_lines.append(f"     Path: `{path}`")

                if result.metadata:
                    response_lines.extend(["", "🏗️  **Layout Details:**"])

                    panes = result.metadata.get("panes", {})
                    if panes:
                        for pane_name, pane_info in panes.items():
                            count = pane_info.get("count", 0)
                            pane_display = pane_name.replace("_", " ").title()
                            response_lines.append(f"   • {pane_display}: {count} elements")

                if result.warnings:
                    response_lines.extend(["", "⚠️  **Warnings:**"])
                    for warning in result.warnings:
                        response_lines.append(f"   • {warning}")

                response_lines.extend(
                    [
                        "",
                        "🎯 **Three-Pane Layout Benefits:**",
                        "   • Clear visual separation of network domains",
                        "   • Easy identification of Core Network boundaries",
                        "   • Dedicated pane for inspection and peering flows",
                        "   • Executive-friendly professional presentation",
                        "   • Optimal for architecture reviews and documentation",
                    ]
                )

            else:
                response_lines = [
                    "❌ **Three-Pane Diagram Generation Failed**",
                    "",
                    "⚠️  **Errors:**",
                ]
                for error in result.errors:
                    response_lines.append(f"   • {error}")

                response_lines.extend(
                    [
                        "",
                        "🔧 **Troubleshooting Steps:**",
                        "   • Verify AWS credentials and permissions",
                        "   • Check if CloudWAN resources exist in specified regions",
                        "   • Ensure AWS Diagram MCP server is available",
                        "   • Try with fewer regions if timeout occurred",
                    ]
                )

            return [TextContent(type="text", text="\n".join(response_lines))]

        except Exception as e:
            self.logger.error(f"Three-pane diagram generation failed: {e}")
            raise ToolError(f"Three-pane diagram generation failed: {str(e)}")

    async def _generate_nfg_inspection_diagram(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Generate NFG inspection flow diagram."""

        try:
            regions = arguments.get("regions")
            output_path = arguments.get("output_path")
            workspace_dir = arguments.get("workspace_dir", str(Path.cwd()))
            diagram_format = arguments.get("format", "png")

            self.logger.info("Generating NFG inspection flow diagram")

            result = await self.diagram_suite.generate_nfg_inspection_flow(
                regions=regions, output_path=output_path, workspace_dir=workspace_dir
            )

            if result.success:
                response_lines = [
                    "✅ **CloudWAN NFG Inspection Flow Diagram Generated Successfully!**",
                    "",
                    "🔍 **Network Function Group Analysis:**",
                    f"   • Elements Analyzed: {result.element_count}",
                    f"   • Connections Mapped: {result.connection_count}",
                    f"   • Generation Time: {result.generation_time:.2f}s",
                    "",
                    "🛡️  **Inspection Flow Features:**",
                    "   • Network Function Groups (NFGs) highlighted",
                    "   • Send-to/Send-via target relationships",
                    "   • Inspection routing paths visualized",
                    "   • Security policy enforcement points",
                    "",
                    "📁 **Generated Files:**",
                ]

                for format_type, path in result.diagram_paths.items():
                    if path:
                        filename = Path(path).name
                        response_lines.append(f"   • {format_type.upper()}: `{filename}`")

                if result.metadata:
                    nfg_count = result.metadata.get("nfg_count", 0)
                    related_count = result.metadata.get("related_count", 0)
                    response_lines.extend(
                        [
                            "",
                            "📈 **Analysis Summary:**",
                            f"   • Network Function Groups: {nfg_count}",
                            f"   • Related Network Elements: {related_count}",
                            f"   • Layout Strategy: {result.metadata.get('layout_strategy', 'NFG Inspection')}",
                        ]
                    )
            else:
                response_lines = [
                    "❌ **NFG Inspection Diagram Generation Failed**",
                    "",
                    "⚠️  **Errors:**",
                ]
                for error in result.errors:
                    response_lines.append(f"   • {error}")

            return [TextContent(type="text", text="\n".join(response_lines))]

        except Exception as e:
            self.logger.error(f"NFG inspection diagram generation failed: {e}")
            raise ToolError(f"NFG inspection diagram generation failed: {str(e)}")

    async def _generate_tgw_peering_diagram(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Generate TGW peering analysis diagram."""

        try:
            regions = arguments.get("regions")
            output_path = arguments.get("output_path")
            workspace_dir = arguments.get("workspace_dir", str(Path.cwd()))
            diagram_format = arguments.get("format", "png")

            self.logger.info("Generating TGW peering analysis diagram")

            result = await self.diagram_suite.generate_tgw_peering_analysis(
                regions=regions, output_path=output_path, workspace_dir=workspace_dir
            )

            if result.success:
                response_lines = [
                    "✅ **CloudWAN TGW Peering Analysis Diagram Generated Successfully!**",
                    "",
                    "🔗 **Transit Gateway Peering Analysis:**",
                    f"   • Elements Analyzed: {result.element_count}",
                    f"   • Connections Mapped: {result.connection_count}",
                    f"   • Generation Time: {result.generation_time:.2f}s",
                    "",
                    "🌐 **Peering Features:**",
                    "   • Transit Gateway peering connections",
                    "   • Cross-account routing relationships",
                    "   • Peering chain visualization",
                    "   • Regional peering topology",
                    "",
                    "📁 **Generated Files:**",
                ]

                for format_type, path in result.diagram_paths.items():
                    if path:
                        filename = Path(path).name
                        response_lines.append(f"   • {format_type.upper()}: `{filename}`")

                if result.metadata:
                    tgw_count = result.metadata.get("tgw_count", 0)
                    peering_connections = result.metadata.get("peering_connections", 0)
                    response_lines.extend(
                        [
                            "",
                            "📈 **Peering Summary:**",
                            f"   • Transit Gateways: {tgw_count}",
                            f"   • Peering Connections: {peering_connections}",
                            f"   • Layout Strategy: {result.metadata.get('layout_strategy', 'TGW Peering')}",
                        ]
                    )
            else:
                response_lines = [
                    "❌ **TGW Peering Diagram Generation Failed**",
                    "",
                    "⚠️  **Errors:**",
                ]
                for error in result.errors:
                    response_lines.append(f"   • {error}")

            return [TextContent(type="text", text="\n".join(response_lines))]

        except Exception as e:
            self.logger.error(f"TGW peering diagram generation failed: {e}")
            raise ToolError(f"TGW peering diagram generation failed: {str(e)}")

    async def _generate_segment_routing_diagram(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Generate segment routing flow diagram."""

        try:
            regions = arguments.get("regions")
            segment_filter = arguments.get("segment_filter")
            output_path = arguments.get("output_path")
            workspace_dir = arguments.get("workspace_dir", str(Path.cwd()))
            diagram_format = arguments.get("format", "png")

            self.logger.info("Generating segment routing flow diagram")

            result = await self.diagram_suite.generate_segment_routing_flow(
                regions=regions,
                segment_filter=segment_filter,
                output_path=output_path,
                workspace_dir=workspace_dir,
            )

            if result.success:
                response_lines = [
                    "✅ **CloudWAN Segment Routing Flow Diagram Generated Successfully!**",
                    "",
                    "🛣️  **Segment Routing Analysis:**",
                    f"   • Elements Analyzed: {result.element_count}",
                    f"   • Connections Mapped: {result.connection_count}",
                    f"   • Generation Time: {result.generation_time:.2f}s",
                    "",
                    "📋 **Routing Features:**",
                    "   • CloudWAN segment routing policies",
                    "   • Inter-segment traffic flows",
                    "   • Routing decision points",
                    "   • Segment isolation boundaries",
                    "",
                    "📁 **Generated Files:**",
                ]

                for format_type, path in result.diagram_paths.items():
                    if path:
                        filename = Path(path).name
                        response_lines.append(f"   • {format_type.upper()}: `{filename}`")

                if result.metadata:
                    segments = result.metadata.get("segments", {})
                    if segments:
                        response_lines.extend(["", "📊 **Segment Analysis:**"])
                        for segment_name, element_count in segments.items():
                            response_lines.append(f"   • {segment_name}: {element_count} elements")

                    orphaned_count = result.metadata.get("orphaned_count", 0)
                    if orphaned_count > 0:
                        response_lines.append(f"   • Unassigned Elements: {orphaned_count}")
            else:
                response_lines = [
                    "❌ **Segment Routing Diagram Generation Failed**",
                    "",
                    "⚠️  **Errors:**",
                ]
                for error in result.errors:
                    response_lines.append(f"   • {error}")

            return [TextContent(type="text", text="\n".join(response_lines))]

        except Exception as e:
            self.logger.error(f"Segment routing diagram generation failed: {e}")
            raise ToolError(f"Segment routing diagram generation failed: {str(e)}")

    async def _generate_diagram_suite(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Generate comprehensive diagram suite."""

        try:
            suite_type = arguments.get("suite_type", "technical")
            output_directory = arguments.get("output_directory", "cloudwan_diagrams")
            regions = arguments.get("regions")
            workspace_dir = arguments.get("workspace_dir", str(Path.cwd()))
            high_resolution = arguments.get("high_resolution", True)
            include_interactive = arguments.get("include_interactive", True)
            max_elements = arguments.get("max_elements", 50)
            generate_all_formats = arguments.get("generate_all_formats", False)

            self.logger.info(f"Generating {suite_type} diagram suite")

            # Configure suite based on type
            suite_config = DiagramSuiteConfiguration(
                output_directory=output_directory,
                high_resolution=high_resolution,
                include_interactive=include_interactive,
                max_elements_per_diagram=max_elements,
                generate_all_formats=generate_all_formats,
            )

            # Generate appropriate suite
            if suite_type == "executive":
                result = await generate_executive_diagram_suite(
                    self.aws_manager, self.config, output_directory, regions
                )
            elif suite_type == "technical":
                result = await generate_technical_diagram_suite(
                    self.aws_manager, self.config, output_directory, regions
                )
            elif suite_type == "operational":
                result = await generate_operational_diagram_suite(
                    self.aws_manager, self.config, output_directory, regions
                )
            else:
                # Custom suite
                result = await self.diagram_suite.generate_complete_suite(
                    suite_config=suite_config, regions=regions, diagram_set=suite_type
                )

            if result.success:
                response_lines = [
                    f"✅ **CloudWAN {suite_type.title()} Diagram Suite Generated Successfully!**",
                    "",
                    "📊 **Suite Statistics:**",
                    f"   • Total Diagrams: {result.total_diagrams}",
                    f"   • Successful: {result.successful_diagrams}",
                    f"   • Failed: {result.failed_diagrams}",
                    f"   • Success Rate: {(result.successful_diagrams / max(result.total_diagrams, 1) * 100):.1f}%",
                    f"   • Generation Time: {result.generation_time:.2f}s",
                    "",
                    f"📁 **Output Directory:** `{result.output_directory}`",
                    "",
                    "🎨 **Generated Diagrams:**",
                ]

                for diagram_name, diagram_result in result.generated_diagrams.items():
                    status = "✅" if diagram_result.success else "❌"
                    response_lines.append(f"   • {diagram_name.replace('_', ' ').title()} {status}")
                    if diagram_result.success:
                        response_lines.append(
                            f"     Elements: {diagram_result.element_count}, Time: {diagram_result.generation_time:.2f}s"
                        )

                if result.summary_report_path:
                    response_lines.extend(
                        [
                            "",
                            "📋 **Reports Generated:**",
                            f"   • Summary Report: `{Path(result.summary_report_path).name}`",
                            "   • README: `README.md`",
                        ]
                    )

                if result.warnings:
                    response_lines.extend(["", "⚠️  **Warnings:**"])
                    for warning in result.warnings[:5]:  # Limit warnings shown
                        response_lines.append(f"   • {warning}")

                response_lines.extend(
                    [
                        "",
                        "🎯 **Suite Benefits:**",
                        "   • Multiple visualization perspectives",
                        "   • Professional AWS iconography",
                        "   • Consistent styling and branding",
                        "   • Executive and technical variants",
                        "   • Ready for presentations and documentation",
                    ]
                )

            else:
                response_lines = [
                    f"❌ **{suite_type.title()} Diagram Suite Generation Failed**",
                    "",
                    "📊 **Partial Results:**",
                    f"   • Successful: {result.successful_diagrams}",
                    f"   • Failed: {result.failed_diagrams}",
                    "",
                    "⚠️  **Errors:**",
                ]
                for error in result.errors[:5]:  # Show first 5 errors
                    response_lines.append(f"   • {error}")

            return [TextContent(type="text", text="\n".join(response_lines))]

        except Exception as e:
            self.logger.error(f"Diagram suite generation failed: {e}")
            raise ToolError(f"Diagram suite generation failed: {str(e)}")

    async def _generate_custom_diagram(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Generate custom diagram with full configuration control."""

        try:
            layout_strategy = LayoutStrategy(arguments.get("layout_strategy", "three_pane"))
            style = DiagramStyle(arguments.get("style", "professional"))
            diagram_format = DiagramFormat(arguments.get("format", "png"))
            regions = arguments.get("regions")
            output_path = arguments.get("output_path")
            workspace_dir = arguments.get("workspace_dir", str(Path.cwd()))

            # Build configuration from arguments
            config = DiagramConfiguration(
                format=diagram_format,
                style=style,
                layout_strategy=layout_strategy,
                show_labels=arguments.get("show_labels", True),
                show_cidr_blocks=arguments.get("show_cidr_blocks", True),
                show_connection_details=arguments.get("show_connection_details", True),
                group_by_region=arguments.get("group_by_region", True),
                group_by_segment=arguments.get("group_by_segment", True),
                max_elements_per_group=arguments.get("max_elements", 20),
                width=arguments.get("width", 1600),
                height=arguments.get("height", 1200),
            )

            self.logger.info(f"Generating custom diagram: {layout_strategy} / {style}")

            # Discover topology
            topology = await self.diagram_suite.topology_discovery.discover_complete_topology(
                regions=regions or self.aws_manager.get_default_regions(),
                include_performance_metrics=False,
                include_security_analysis=False,
                max_depth=2,
            )

            # Generate diagram
            result = await self.diagram_suite.advanced_renderer.generate_diagram(
                topology=topology,
                config=config,
                output_path=output_path,
                workspace_dir=workspace_dir,
            )

            if result.success:
                response_lines = [
                    "✅ **Custom CloudWAN Diagram Generated Successfully!**",
                    "",
                    "⚙️  **Configuration:**",
                    f"   • Layout Strategy: {layout_strategy.value.replace('_', ' ').title()}",
                    f"   • Style: {style.value.title()}",
                    f"   • Format: {diagram_format.value.upper()}",
                    f"   • Dimensions: {config.width}x{config.height}",
                    "",
                    "📊 **Analysis Results:**",
                    f"   • Elements Processed: {result.element_count}",
                    f"   • Connections Mapped: {result.connection_count}",
                    f"   • Generation Time: {result.generation_time:.2f}s",
                    "",
                    "📁 **Generated Files:**",
                ]

                for format_type, path in result.diagram_paths.items():
                    if path:
                        filename = Path(path).name
                        response_lines.append(f"   • {format_type.upper()}: `{filename}`")
                        response_lines.append(f"     Path: `{path}`")

                if result.metadata:
                    response_lines.extend(
                        [
                            "",
                            "🏗️  **Layout Metadata:**",
                            f"   • Strategy: {result.metadata.get('layout_strategy', 'Custom')}",
                        ]
                    )

                    # Add strategy-specific details
                    if "panes" in result.metadata:
                        panes = result.metadata["panes"]
                        for pane_name, pane_info in panes.items():
                            count = pane_info.get("count", 0)
                            response_lines.append(
                                f"   • {pane_name.replace('_', ' ').title()}: {count} elements"
                            )

                    if "segments" in result.metadata:
                        segments = result.metadata["segments"]
                        response_lines.append(f"   • Segments: {len(segments)} identified")

                    if "regions" in result.metadata:
                        regions_meta = result.metadata["regions"]
                        response_lines.append(f"   • Regions: {len(regions_meta)} analyzed")

            else:
                response_lines = [
                    "❌ **Custom Diagram Generation Failed**",
                    "",
                    "⚠️  **Errors:**",
                ]
                for error in result.errors:
                    response_lines.append(f"   • {error}")

            return [TextContent(type="text", text="\n".join(response_lines))]

        except Exception as e:
            self.logger.error(f"Custom diagram generation failed: {e}")
            raise ToolError(f"Custom diagram generation failed: {str(e)}")


def register_cloudwan_diagrams_tools(
    server: Server, aws_manager: AWSClientManager, config: CloudWANConfig
):
    """Register CloudWAN diagrams tools with the MCP server."""

    tool = CloudWANProfessionalDiagramsTool(aws_manager, config)

    for mcp_tool in tool.get_tools():

        @server.tool(mcp_tool.name, mcp_tool.description, mcp_tool.inputSchema)
        async def handle_tool(
            arguments: Dict[str, Any], tool_name: str = mcp_tool.name
        ) -> List[TextContent]:
            return await tool.execute_tool(tool_name, arguments)

    return tool
