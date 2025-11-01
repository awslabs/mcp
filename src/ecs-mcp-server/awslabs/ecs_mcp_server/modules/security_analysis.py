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
This module provides tools and prompts for analyzing ECS security configurations.
"""

import logging
import os

from fastmcp import FastMCP

from awslabs.ecs_mcp_server.api.security_analysis import (
    format_clusters_for_display,
    get_clusters_with_metadata,
)

logger = logging.getLogger(__name__)


def register_module(mcp: FastMCP) -> None:
    """Register security analysis module tools and prompts with the MCP server."""

    @mcp.tool(name="analyze_ecs_security", annotations=None)
    async def mcp_analyze_ecs_security() -> str:
        """
        List ECS clusters available for security analysis.

        The region is determined from the AWS_REGION environment variable (defaults to 'us-east-1').

        This tool lists all ECS clusters in the configured AWS region, providing
        an overview of available clusters that can be analyzed for security issues.

        Interactive Workflow:

        Workflow:

        Step 1: List Available Clusters
           - Call with NO parameters to list clusters in configured region
           - Returns formatted list of available clusters with metadata
           - User reviews the list to see what clusters are available

        Note: Future versions will support cluster_names parameter for detailed analysis

        Usage Example:

        Example - List clusters in configured region:
            analyze_ecs_security()
            # Returns list of clusters in AWS_REGION for selection

        Cluster Information Provided:
        - Cluster name and ARN
        - Current status (ACTIVE, INACTIVE, etc.)
        - Running tasks count
        - Active services count
        - Registered container instances count
        - Resource tags

        Returns:
            Formatted list of available clusters for selection

        Error Handling:
            - No clusters found: Returns helpful message with cluster creation guidance
        """
        try:
            # List clusters for user selection
            region = os.environ.get("AWS_REGION", "us-east-1")
            logger.info(f"Listing clusters in region '{region}' for user selection")
            clusters = await get_clusters_with_metadata()
            return format_clusters_for_display(clusters)

        except Exception as e:
            import traceback

            error_msg = f"Error during security analysis: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"❌ {error_msg}\n\nDetailed error:\n{traceback.format_exc()}"

    # Register prompt patterns for security analysis

    @mcp.prompt("analyze ecs security")
    def analyze_ecs_security_prompt():
        """User wants to analyze ECS security"""
        return ["analyze_ecs_security"]

    @mcp.prompt("check ecs security")
    def check_ecs_security_prompt():
        """User wants to check ECS security"""
        return ["analyze_ecs_security"]

    @mcp.prompt("ecs security audit")
    def ecs_security_audit_prompt():
        """User wants to perform an ECS security audit"""
        return ["analyze_ecs_security"]

    @mcp.prompt("security best practices")
    def security_best_practices_prompt():
        """User wants to check security best practices"""
        return ["analyze_ecs_security"]

    @mcp.prompt("security recommendations")
    def security_recommendations_prompt():
        """User wants security recommendations"""
        return ["analyze_ecs_security"]

    @mcp.prompt("scan ecs clusters")
    def scan_ecs_clusters_prompt():
        """User wants to scan ECS clusters for security issues"""
        return ["analyze_ecs_security"]

    @mcp.prompt("ecs security scan")
    def ecs_security_scan_prompt():
        """User wants to perform an ECS security scan"""
        return ["analyze_ecs_security"]

    @mcp.prompt("list ecs clusters")
    def list_ecs_clusters_prompt():
        """User wants to list ECS clusters"""
        return ["analyze_ecs_security"]
