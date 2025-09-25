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
This module provides tools and prompts for ECS security analysis.
"""

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from awslabs.ecs_mcp_server.api.security_analysis import (
    SecurityAnalysisAction,
    ecs_security_analysis_tool,
)

def register_module(mcp: FastMCP) -> None:
    """Register security analysis module tools and prompts with the MCP server."""

    @mcp.tool(
        name="ecs_security_analysis_tool",
        annotations=None,
    )
    async def mcp_ecs_security_analysis_tool(
        action: SecurityAnalysisAction = "analyze_cluster_security",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        ECS security analysis tool for analyzing INDIVIDUAL clusters selected by the user.

        IMPORTANT WORKFLOW:
        1. Let the user specify their AWS region (defaults to us-east-1 if not specified)
        2. Use 'list_clusters' to show available clusters in that region
        3. Let the user choose which specific cluster they want to analyze
        4. Then analyze only that selected cluster - DO NOT analyze all clusters automatically
        
        This tool analyzes ONE cluster at a time in a SPECIFIC region based on user selection.
        Use the 'action' parameter to specify which security analysis operation to perform.

        ## Available Actions and Parameters:

        ### 1. list_clusters
        List all available ECS clusters in a SPECIFIC region for user selection
        - IMPORTANT: Always ask user for their AWS region first
        - Optional: region (default: us-east-1 - but user should specify their region)
        - Example: action="list_clusters", parameters={"region": "us-west-2"}
        - Common regions: us-east-1, us-west-2, eu-west-1, ap-southeast-1

        ### 2. select_cluster_for_analysis
        Interactive cluster selection with analysis options - RECOMMENDED for user-friendly experience
        - IMPORTANT: Ask user for their AWS region first
        - Optional: region (specify user's region), cluster_name, analysis_type
        - Example: action="select_cluster_for_analysis", parameters={"region": "eu-west-1"}

        ### 3. analyze_cluster_security
        Comprehensive security analysis of an ECS cluster
        - Required: cluster_name
        - Optional: region (default: us-east-1)
        - Example: action="analyze_cluster_security",
                   parameters={"cluster_name": "my-cluster", "region": "us-west-2"}

        ### 4. generate_security_report
        Generate detailed security report with enhanced formatting and filtering options
        - Required: cluster_name
        - Optional: region, format, severity_filter, category_filter, show_details
        - Formats: "summary" (default), "detailed", "json", "executive"
        - Severity filters: ["High"], ["Medium"], ["High", "Medium"], etc.
        - Category filters: ["network_security"], ["container_security"], ["iam_security"], etc.
        - show_details: true/false (expand medium/low issue details)
        - Examples:
          * Basic report: {"cluster_name": "my-cluster"}
          * High priority only: {"cluster_name": "my-cluster", "severity_filter": ["High"]}
          * Network issues: {"cluster_name": "my-cluster", "category_filter": ["network_security"]}
          * Full details: {"cluster_name": "my-cluster", "format": "detailed"}
          * Executive summary: {"cluster_name": "my-cluster", "format": "executive"}
          * JSON export: {"cluster_name": "my-cluster", "format": "json"}

        ### 5. get_security_recommendations
        Get filtered security recommendations for a specific cluster
        - Required: cluster_name
        - Optional: region, severity_filter (high/medium/low), category_filter, limit (default: 5)
        - Example: action="get_security_recommendations",
                   parameters={"cluster_name": "my-cluster", "severity_filter": "high"}

        ### 6. check_compliance_status
        Check compliance against security best practices for a specific cluster
        - Required: cluster_name
        - Optional: region, compliance_framework (default: aws-foundational)
        - Example: action="check_compliance_status",
                   parameters={"cluster_name": "my-cluster", "compliance_framework": "aws-foundational"}

        ## RECOMMENDED WORKFLOW:
        1. Ask the user for their AWS region (e.g., us-east-1, us-west-2, eu-west-1)
        2. Use 'list_clusters' or 'select_cluster_for_analysis' with the user's region
        3. Let the user choose which specific cluster they want to analyze
        4. Analyze only the user-selected cluster in their specified region
        5. Provide specific recommendations for that cluster only

        ## NATURAL LANGUAGE PROMPTS CUSTOMERS CAN USE:
        
        ### Cluster Discovery:
        • "What clusters do I have?"
        • "Show me my ECS clusters"
        • "List clusters in us-west-2"
        • "Find my clusters"
        
        ### Security Analysis:
        • "Analyze my ECS security"
        • "Check security issues in my cluster"
        • "Is my ECS secure?"
        • "How secure is my cluster?"
        • "Audit my ECS security"
        
        ### Finding Issues:
        • "Show me security vulnerabilities"
        • "What security problems do I have?"
        • "Find security risks"
        • "Check for security gaps"
        
        ### Reports and Compliance:
        • "Generate a security report"
        • "Create security assessment"
        • "Check compliance"
        • "Security review for my cluster"
        
        ### Specific Security Areas:
        • "Check container security"
        • "Analyze network security"
        • "Review security groups"
        • "Check IAM security"
        
        ### Action-Oriented:
        • "Fix security issues"
        • "Improve my security"
        • "Secure my ECS"
        • "Harden security"

        Parameters:
            action: The security analysis action to perform
            parameters: Action-specific parameters dictionary

        Returns:
            Dictionary containing security analysis results
        """
        return await ecs_security_analysis_tool(action, parameters)

    # Register comprehensive prompts for security analysis
    
    # Core security analysis prompts
    @mcp.prompt("security analysis")
    def security_analysis_prompt():
        """User wants to perform security analysis"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("analyze my ECS security")
    def analyze_ecs_security_prompt():
        """User wants to analyze ECS security"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("check ECS security")
    def check_ecs_security_prompt():
        """User wants to check ECS security"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("ECS security audit")
    def ecs_security_audit_prompt():
        """User wants an ECS security audit"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("security recommendations")
    def security_recommendations_prompt():
        """User wants security recommendations"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("security vulnerabilities")
    def security_vulnerabilities_prompt():
        """User wants to find security vulnerabilities"""
        return ["ecs_security_analysis_tool"]

    # Cluster discovery prompts
    @mcp.prompt("list my clusters")
    def list_my_clusters_prompt():
        """User wants to list their ECS clusters"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("show ECS clusters")
    def show_ecs_clusters_prompt():
        """User wants to see ECS clusters"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("what clusters do I have")
    def what_clusters_prompt():
        """User wants to know what clusters they have"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("find my clusters")
    def find_clusters_prompt():
        """User wants to find their clusters"""
        return ["ecs_security_analysis_tool"]

    # Security issues and problems
    @mcp.prompt("security issues")
    def security_issues_prompt():
        """User wants to find security issues"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("security problems")
    def security_problems_prompt():
        """User wants to find security problems"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("security risks")
    def security_risks_prompt():
        """User wants to identify security risks"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("security gaps")
    def security_gaps_prompt():
        """User wants to find security gaps"""
        return ["ecs_security_analysis_tool"]

    # Compliance and best practices
    @mcp.prompt("security compliance")
    def security_compliance_prompt():
        """User wants to check security compliance"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("AWS security best practices")
    def aws_security_best_practices_prompt():
        """User wants to check AWS security best practices"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("compliance check")
    def compliance_check_prompt():
        """User wants a compliance check"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("security standards")
    def security_standards_prompt():
        """User wants to check against security standards"""
        return ["ecs_security_analysis_tool"]

    # Reports and documentation
    @mcp.prompt("security report")
    def security_report_prompt():
        """User wants a security report"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("generate security report")
    def generate_security_report_prompt():
        """User wants to generate a security report"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("security assessment")
    def security_assessment_prompt():
        """User wants a security assessment"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("security review")
    def security_review_prompt():
        """User wants a security review"""
        return ["ecs_security_analysis_tool"]

    # Container and ECS specific prompts
    @mcp.prompt("container security")
    def container_security_prompt():
        """User wants to check container security"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("ECS security")
    def ecs_security_prompt():
        """User wants ECS security analysis"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("task security")
    def task_security_prompt():
        """User wants to check task security"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("service security")
    def service_security_prompt():
        """User wants to check service security"""
        return ["ecs_security_analysis_tool"]

    # Network and infrastructure security
    @mcp.prompt("network security")
    def network_security_prompt():
        """User wants to check network security"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("security groups")
    def security_groups_prompt():
        """User wants to check security groups"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("IAM security")
    def iam_security_prompt():
        """User wants to check IAM security"""
        return ["ecs_security_analysis_tool"]

    # Action-oriented prompts
    @mcp.prompt("fix security issues")
    def fix_security_issues_prompt():
        """User wants to fix security issues"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("improve security")
    def improve_security_prompt():
        """User wants to improve security"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("secure my ECS")
    def secure_ecs_prompt():
        """User wants to secure their ECS"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("harden security")
    def harden_security_prompt():
        """User wants to harden security"""
        return ["ecs_security_analysis_tool"]

    # Question-based prompts
    @mcp.prompt("is my ECS secure")
    def is_ecs_secure_prompt():
        """User wants to know if their ECS is secure"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("how secure is my cluster")
    def how_secure_cluster_prompt():
        """User wants to know how secure their cluster is"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("what security issues do I have")
    def what_security_issues_prompt():
        """User wants to know what security issues they have"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("show me security problems")
    def show_security_problems_prompt():
        """User wants to see security problems"""
        return ["ecs_security_analysis_tool"]

    # Enhanced reporting prompts
    @mcp.prompt("detailed security report")
    def detailed_security_report_prompt():
        """User wants a detailed security report"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("executive security summary")
    def executive_security_summary_prompt():
        """User wants an executive security summary"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("high priority security issues")
    def high_priority_security_issues_prompt():
        """User wants to see only high priority security issues"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("high priority security issues")
    def high_priority_security_issues_prompt():
        """User wants to see high priority security issues"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("show all security details")
    def show_all_security_details_prompt():
        """User wants to see all security details"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("security report for leadership")
    def security_report_leadership_prompt():
        """User wants a security report for leadership"""
        return ["ecs_security_analysis_tool"]

    @mcp.prompt("export security data")
    def export_security_data_prompt():
        """User wants to export security data"""
        return ["ecs_security_analysis_tool"]