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
This module provides comprehensive security analysis for ECS clusters.
"""

import logging
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from pydantic import Field

from awslabs.ecs_mcp_server.api.security_analysis import analyze_ecs_security

logger = logging.getLogger(__name__)


def register_module(mcp: FastMCP) -> None:
    """Register security analysis module tools and prompts with the MCP server."""

    @mcp.tool(name="analyze_ecs_security", annotations=None)
    async def mcp_analyze_ecs_security(
        cluster_names: List[str] = Field(  # noqa: B008
            ...,
            description=(
                "REQUIRED: List of ECS cluster names to analyze. "
                "User must explicitly specify which clusters to analyze. "
                "Example: ['my-cluster', 'prod-cluster']"
            ),
        ),
        regions: Optional[List[str]] = Field(  # noqa: B008
            default=None,
            description=(
                "List of AWS regions where the clusters are located. "
                "Defaults to ['us-east-1'] if not specified. "
                "Example: ['us-east-1', 'us-west-2']"
            ),
        ),
    ) -> Dict[str, Any]:
        """
        Analyze ECS cluster security configurations and provide recommendations.

        Use this tool when you need to assess the security posture of ECS clusters,
        identify security misconfigurations, and get actionable remediation steps.

        IMPORTANT - REQUIRED USER INTERACTION BEFORE CALLING THIS TOOL:

        STEP 1 - ASK FOR REGION FIRST:
        You MUST ask the user: "Which AWS region would you like to analyze for ECS security issues?"
        - Provide common options: us-east-1 (default), us-west-2, eu-west-1, ap-southeast-1
        - Wait for user to specify the region

        STEP 2 - LIST CLUSTERS IN THAT REGION:
        Use ecs_resource_management tool with ListClusters for the user-specified region
        Show the user: "I found these clusters in {region}: [list]"

        STEP 3 - ASK USER TO SELECT CLUSTERS:
        Ask: "Which cluster(s) would you like me to analyze?"
        Allow single or multiple selections

        STEP 4 - CALL THIS TOOL:
        Only after completing steps 1-3, call this tool with selected clusters and region

        STEP 5 - AFTER ANALYSIS:
        Ask: "Would you like to analyze clusters in a different region?"
        If yes, repeat from STEP 1

        USAGE EXAMPLES:
        1. Analyze specific clusters in default region (us-east-1):
           cluster_names: ["my-cluster", "prod-cluster"]

        2. Analyze specific clusters in specific region:
           cluster_names: ["my-cluster"]
           regions: ["us-west-2"]

        3. Analyze same-named clusters across multiple regions:
           cluster_names: ["prod-cluster"]
           regions: ["us-east-1", "us-west-2"]
           Note: This will look for "prod-cluster" in both regions

        MULTI-REGION WORKFLOW:
        - Analyze one region at a time for better user experience
        - After showing results, ask: "Would you like to analyze another region?"
        - If yes, repeat the workflow for the new region
        - This allows users to focus on one region's issues before moving to the next

        WORKFLOW:
        1. List available clusters using ecs_resource_management tool
        2. Ask user to select which clusters to analyze
        3. Run this tool with the selected cluster names
        4. Review the security recommendations organized by severity and category
        5. Follow the remediation steps provided for each security issue
        6. Re-run the analysis after implementing fixes to verify improvements

        The analysis includes:
        - Container Insights monitoring configuration
        - Execute command logging settings
        - Cluster status and availability
        - CloudWatch logging configuration
        - Log encryption settings

        Parameters:
            cluster_names: REQUIRED list of cluster names to analyze.
                          User must explicitly select which clusters to analyze.
                          Example: ["my-cluster", "prod-cluster"]

            regions: Optional list of AWS regions where clusters are located.
                    Defaults to ["us-east-1"] if not specified.
                    Example: ["us-east-1", "us-west-2"]

        Returns:
            Dictionary containing:
            - status: "success" or "error"
            - total_clusters_analyzed: Number of clusters analyzed
            - total_recommendations: Total number of security recommendations
            - results: List of analysis results per cluster with recommendations and summary

        PRESENTATION GUIDELINES:

        STRUCTURE YOUR RESPONSE IN TWO SECTIONS:

        SECTION 1 - EXECUTIVE SUMMARY (Show this first):
        ```
        ## Security Analysis Results for {cluster_name}

        Summary: Found {total} security recommendations
        🔴 High: {count} issues
        🟠 Medium: {count} issues
        🟡 Low: {count} issues

        ### Issues Found:
        1. 🔴 [HIGH] Execute Command Logging Not Configured
           - ECS Exec sessions are not being logged (NONE setting)
           - Cluster: my-ecs-cluster | Region: us-east-1

        2. 🟠 [MEDIUM] CloudWatch Log Group Not Configured
           - No CloudWatch log group for ECS Exec audit trails
           - Cluster: my-ecs-cluster | Region: us-east-1
        ```

        SECTION 2 - DETAILED REMEDIATION (Show this after summary):
        For each issue, provide:
        - Full explanation of the security risk
        - Step-by-step remediation commands
        - AWS documentation links

        FORMATTING RULES:
        1. Use AWS Trusted Advisor color coding:
           🔴 High (critical), 🟠 Medium (important), 🟡 Low (minor)
        2. Group by severity: High → Medium → Low
        3. Show resource hierarchy: Cluster: {name} | Region: {region}
        4. Include CLI commands in code blocks
        5. Link to AWS documentation for each issue type

        CRITICAL - YOU MUST ASK FOR REGION FIRST:

        DO NOT automatically list clusters without asking for region first!

        Correct workflow:
        1. Ask: "Which AWS region? (us-east-1, us-west-2, eu-west-1, etc.)"
        2. User specifies region (e.g., "us-west-2")
        3. List clusters in that specific region
        4. Ask user to select clusters
        5. Run this tool with selected clusters and region
        6. After results, ask: "Analyze another region?"

        Wrong workflow (DO NOT DO THIS):
        ❌ Listing clusters without asking for region first
        ❌ Assuming us-east-1 without asking user
        ❌ Not offering to check other regions after analysis
        """
        logger.info(f"Security analysis requested - clusters: {cluster_names}, regions: {regions}")
        return await analyze_ecs_security(cluster_names=cluster_names, regions=regions)

    @mcp.prompt("analyze ecs security")
    def security_analysis_prompt() -> List[str]:
        """User wants to analyze ECS security"""
        logger.info("Security analysis prompt triggered")
        return ["analyze_ecs_security"]

    @mcp.prompt("check ecs security")
    def security_check_prompt() -> List[str]:
        """User wants to check ECS security"""
        logger.info("Security check prompt triggered")
        return ["analyze_ecs_security"]
