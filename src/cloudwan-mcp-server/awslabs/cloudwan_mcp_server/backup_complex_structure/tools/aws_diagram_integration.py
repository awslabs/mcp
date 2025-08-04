"""
AWS Diagram Integration for CloudWAN topology visualization.

This module provides integration with the AWS Diagram MCP server to generate
professional cloud architecture diagrams using the Python diagrams package.
It integrates with the CloudWAN topology discovery module to create diagrams
of network infrastructure.
"""

import logging
import os
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path

from .visualization.topology_renderer import (
    NetworkTopologyRenderer,
    RenderingOptions,
    LayoutType,
    ColorScheme,
)
from .visualization.topology_discovery import NetworkTopology


class AWSDiagramIntegration:
    """Integration with AWS Diagram MCP server for professional network diagrams."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate_topology_diagram(
        self,
        topology: NetworkTopology,
        output_path: Optional[str] = None,
        layout_type: LayoutType = LayoutType.LAYERED,
        color_scheme: ColorScheme = ColorScheme.CORPORATE,
        show_labels: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate AWS diagram for CloudWAN topology.

        Args:
            topology: NetworkTopology object with elements and connections
            output_path: Path to save the diagram (optional)
            layout_type: Layout algorithm to use (LAYERED is recommended for network diagrams)
            color_scheme: Color palette to use
            show_labels: Whether to show node labels

        Returns:
            Dictionary with diagram generation results
        """
        # Create renderer with options
        renderer = NetworkTopologyRenderer()
        options = RenderingOptions(
            layout_type=layout_type,
            color_scheme=color_scheme,
            show_labels=show_labels,
            width=1600,  # Wider diagram for better readability
            height=1000,  # Taller diagram for more vertical space
            dpi=300,  # Higher DPI for better quality
        )

        # Generate diagram code
        diagram_code = renderer.generate_aws_diagram_code(topology, options)

        # Determine output path if not provided
        if not output_path:
            output_dir = Path(tempfile.gettempdir()) / "cloudwan_diagrams"
            output_dir.mkdir(exist_ok=True)
            output_path = str(output_dir / "cloudwan_topology")

        # Try to use AWS Diagram MCP server if available
        if self.is_available():
            return self._generate_with_mcp(diagram_code, output_path)
        else:
            # Fall back to direct rendering if MCP server not available
            return self._generate_with_fallback(topology, output_path, options)

    def _generate_with_mcp(
        self,
        code: str,
        filename: str,
        workspace_dir: Optional[str] = None,
        timeout: int = 90,
    ) -> Dict[str, Any]:
        """
        Generate diagram using AWS Diagram MCP server.

        Args:
            code: Python code using diagrams package
            filename: Output filename (without extension)
            workspace_dir: Directory to save the diagram (optional)
            timeout: Generation timeout in seconds

        Returns:
            Dictionary with diagram generation results
        """
        try:
            # Try to import and use AWS Diagram MCP server
            from mcp__aws_diagram_server__generate_diagram import generate_diagram

            # Determine workspace directory if not provided
            if workspace_dir is None:
                workspace_dir = os.path.dirname(filename)
                if not workspace_dir:
                    workspace_dir = tempfile.gettempdir()

            # Generate the diagram using MCP server
            self.logger.info(f"Generating diagram using AWS Diagram MCP server: {filename}")
            result = generate_diagram(
                code=code,
                filename=os.path.basename(filename),
                workspace_dir=workspace_dir,
                timeout=timeout,
            )

            return {
                "success": True,
                "diagram_path": result.get("path", result.get("diagram_path")),
                "status": result.get("status", "completed"),
                "message": result.get("message", "Diagram generated successfully"),
                "using": "aws_diagram_server",
            }

        except ImportError as e:
            self.logger.warning(f"AWS Diagram MCP server not available: {e}")
            return {
                "success": False,
                "error": f"AWS Diagram MCP server not available: {e}",
                "fallback_required": True,
            }
        except Exception as e:
            self.logger.error(f"AWS Diagram generation failed: {e}")
            return {"success": False, "error": str(e), "fallback_required": True}

    def _generate_with_fallback(
        self, topology: NetworkTopology, output_path: str, options: RenderingOptions
    ) -> Dict[str, Any]:
        """
        Generate diagram using matplotlib fallback renderer.

        Args:
            topology: NetworkTopology object
            output_path: Path to save the diagram
            options: RenderingOptions object

        Returns:
            Dictionary with diagram generation results
        """
        try:
            self.logger.info(
                "AWS Diagram MCP server not available, using matplotlib fallback renderer"
            )

            # Create renderer and render static diagram
            renderer = NetworkTopologyRenderer()
            diagram_path = renderer.render_static_matplotlib(
                topology, f"{output_path}.png", options
            )

            return {
                "success": True,
                "diagram_path": diagram_path,
                "status": "completed",
                "message": "Diagram generated with matplotlib fallback renderer",
                "using": "matplotlib",
            }

        except Exception as e:
            self.logger.error(f"Fallback diagram generation failed: {e}")
            return {"success": False, "error": str(e), "using": "matplotlib"}

    def is_available(self) -> bool:
        """Check if AWS Diagram MCP server is available."""
        try:
            from mcp__aws_diagram_server__generate_diagram import generate_diagram

            return True
        except ImportError:
            return False
