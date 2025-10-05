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

from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from pydantic import Field

from awslabs.ecs_mcp_server.api.security_analysis import analyze_ecs_security


def register_module(mcp: FastMCP) -> None:
    """Register security analysis module tools and prompts with the MCP server."""

    @mcp.tool(name="analyze_ecs_security", annotations=None)
    async def mcp_analyze_ecs_security(
        cluster_names: Optional[List[str]] = Field(  # noqa: B008
            default=None,
            description=(
                "List of ECS cluster names to analyze (optional, will discover all if not provided)"
            ),
        ),
        regions: Optional[List[str]] = Field(  # noqa: B008
            default=None,
            description="List of AWS regions to analyze (optional, default: us-east-1)",
        ),
    ) -> Dict[str, Any]:
        """
        Analyze ECS cluster security configurations and provide recommendations.

        Use this tool when you need to assess the security posture of ECS clusters,
        identify security misconfigurations, and get actionable remediation steps.

        USAGE INSTRUCTIONS:
        1. Run this tool to analyze security configurations of your ECS clusters
        2. Review the security recommendations organized by severity and category
        3. Follow the remediation steps provided for each security issue
        4. Re-run the analysis after implementing fixes to verify improvements

        The analysis includes:
        - Container Insights monitoring configuration
        - Execute command logging settings
        - Cluster status and availability
        - IAM security configurations
        - CloudWatch logging setup

        Parameters:
            cluster_names: Optional list of specific cluster names to analyze.
                          If not provided, all clusters in the region will be analyzed.
            regions: Optional list of AWS regions. Defaults to ["us-east-1"].

        Returns:
            Dictionary containing:
            - status: "success" or "error"
            - total_clusters_analyzed: Number of clusters analyzed
            - total_recommendations: Total number of security recommendations
            - results: List of analysis results per cluster, each containing:
                - cluster_name: Name of the analyzed cluster
                - recommendations: List of security recommendations with:
                    - title: Brief description of the issue
                    - severity: Critical, High, Medium, or Low
                    - category: Security category (Monitoring, Logging, IAM, etc.)
                    - resource: Affected resource name
                    - issue: Detailed description of the security issue
                    - recommendation: What should be done
                    - remediation_steps: Step-by-step fix instructions
                - summary: Statistics including:
                    - total_issues: Total number of issues found
                    - by_severity: Count of issues by severity level
                    - by_category: Count of issues by category
        """
        return await analyze_ecs_security(cluster_names=cluster_names, regions=regions)

    # Prompt patterns for security analysis
    @mcp.prompt("security analysis")
    def security_analysis_prompt():
        """User wants to analyze ECS security"""
        return ["analyze_ecs_security"]

    @mcp.prompt("security check")
    def security_check_prompt():
        """User wants to check ECS security"""
        return ["analyze_ecs_security"]

    @mcp.prompt("security audit")
    def security_audit_prompt():
        """User wants to audit ECS security"""
        return ["analyze_ecs_security"]

    @mcp.prompt("security recommendations")
    def security_recommendations_prompt():
        """User wants security recommendations"""
        return ["analyze_ecs_security"]
