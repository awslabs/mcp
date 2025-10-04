# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Security Analysis module for ECS MCP Server.
This module provides tools and prompts for comprehensive ECS security analysis.
"""

from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from pydantic import Field

from awslabs.ecs_mcp_server.api.security_analysis import analyze_ecs_security


def register_module(mcp: FastMCP) -> None:
    """
    Register security analysis module tools and prompts with the MCP server.

    Args:
        mcp: FastMCP server instance to register tools and prompts with

    Returns:
        None
    """

    @mcp.tool(name="analyze_ecs_security", annotations=None)
    async def mcp_analyze_ecs_security(
        cluster_names: Optional[List[str]] = Field(  # noqa: B008
            default=None,
            description=(
                "List of ECS cluster names to analyze. "
                "If not provided, all clusters will be analyzed."
            ),
        ),
        regions: Optional[List[str]] = Field(  # noqa: B008
            default=None,
            description=("List of AWS regions to analyze. If not provided, uses default region."),
        ),
    ) -> Dict[str, Any]:
        """
        Use this when a user wants to perform security analysis on their ECS infrastructure.

        This tool provides comprehensive security analysis for ECS clusters, identifying
        potential security risks and providing actionable recommendations. It analyzes
        cluster configurations, monitoring settings, and security best practices.

        USAGE INSTRUCTIONS:
        1. Run this tool to analyze security posture of ECS clusters
        2. Review the security recommendations organized by severity and category
        3. Follow the remediation steps provided for each finding
        4. Re-run the analysis after implementing fixes to verify improvements

        The analysis includes:
        - Container Insights monitoring status
        - Execute command security configuration
        - Cluster status and availability
        - Security best practices compliance

        Parameters:
            cluster_names: Optional list of specific cluster names to analyze
            regions: Optional list of AWS regions to analyze

        Returns:
            Dictionary containing security analysis results with recommendations
        """
        return await analyze_ecs_security(
            cluster_names=cluster_names,
            regions=regions,
        )

    # Prompt patterns for security analysis
    @mcp.prompt("security analysis")
    def security_analysis_prompt():
        """
        User wants security analysis.

        Returns:
            List of tool names to suggest for security analysis
        """
        return ["analyze_ecs_security"]

    @mcp.prompt("security check")
    def security_check_prompt():
        """
        User wants to check security.

        Returns:
            List of tool names to suggest for security checks
        """
        return ["analyze_ecs_security"]

    @mcp.prompt("ecs security")
    def ecs_security_prompt():
        """
        User wants ECS security analysis.

        Returns:
            List of tool names to suggest for ECS security analysis
        """
        return ["analyze_ecs_security"]

    @mcp.prompt("security audit")
    def security_audit_prompt():
        """
        User wants security audit.

        Returns:
            List of tool names to suggest for security audits
        """
        return ["analyze_ecs_security"]
