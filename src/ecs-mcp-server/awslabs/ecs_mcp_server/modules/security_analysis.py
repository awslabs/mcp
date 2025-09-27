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

from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from awslabs.ecs_mcp_server.api.security_analysis import (
    SecurityAnalysisAction,
    ecs_security_analysis_tool,
)


def register_security_analysis_prompts(mcp: FastMCP, prompt_groups: Dict[str, List[str]]) -> None:
    """
    Register multiple prompt patterns that all return the same tool.

    Args:
        mcp: FastMCP instance
        prompt_groups: Dict mapping descriptions to pattern lists
    """
    for description, patterns in prompt_groups.items():
        for pattern in patterns:

            def create_handler(pattern_val: str, desc: str):
                def prompt_handler():
                    return ["ecs_security_analysis_tool"]

                # Create a valid function name from the pattern
                safe_name = (
                    pattern_val.replace(" ", "_")
                    .replace(".*", "any")
                    .replace("'", "")
                    .replace('"', "")
                )
                safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in safe_name)
                prompt_handler.__name__ = f"{safe_name}_prompt"
                prompt_handler.__doc__ = desc
                return prompt_handler

            mcp.prompt(pattern)(create_handler(pattern, description))


def register_module(mcp: FastMCP) -> None:
    """Register security analysis module tools and prompts with the MCP server."""

    @mcp.tool(
        name="ecs_security_analysis_tool",
        annotations=None,
    )
    async def mcp_ecs_security_analysis_tool(
        action: SecurityAnalysisAction = "list_clusters",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        ECS security analysis tool with comprehensive security assessment capabilities.

        This tool provides comprehensive security analysis for ECS clusters, identifying
        vulnerabilities, misconfigurations, and compliance issues across your containerized
        infrastructure.

        ## Available Actions and Parameters:

        ### 1. list_clusters
        List available ECS clusters for security analysis
        - Optional: region (AWS region to search, default: us-east-1)
        - Example: action="list_clusters", parameters={"region": "us-east-1"}

        ### 2. select_cluster_for_analysis
        Interactive cluster selection with analysis options
        - Optional: cluster_name (Name of the ECS cluster to analyze),
                   region (AWS region, default: us-east-1),
                   analysis_type (Type of analysis: comprehensive, quick, report, compliance)
        - Example: action="select_cluster_for_analysis",
                   parameters={"cluster_name": "my-cluster", "region": "us-east-1",
                              "analysis_type": "comprehensive"}

        ### 3. analyze_cluster_security
        Comprehensive security analysis of an ECS cluster
        - Required: cluster_name (Name of the ECS cluster to analyze)
        - Optional: region (AWS region, default: us-east-1)
        - Example: action="analyze_cluster_security",
                   parameters={"cluster_name": "my-cluster", "region": "us-east-1"}

        ### 4. generate_security_report
        Generate detailed security reports with multiple format options
        - Required: cluster_name (Name of the ECS cluster)
        - Optional: region (AWS region, default: us-east-1),
                   format (Report format: summary, detailed, json, executive),
                   severity_filter (Filter by severity: High, Medium, Low),
                   category_filter (Filter by category: network_security, container_security, etc.),
                   show_details (Show full details for all issues: true/false)
        - Example: action="generate_security_report",
                   parameters={"cluster_name": "my-cluster", "format": "summary",
                              "severity_filter": "High"}

        ### 5. get_security_recommendations
        Get filtered security recommendations with implementation guidance
        - Required: cluster_name (Name of the ECS cluster)
        - Optional: region (AWS region, default: us-east-1),
                   severity_filter (Filter by severity: High, Medium, Low),
                   category_filter (Filter by category),
                   limit (Maximum number of recommendations to return, default: 10)
        - Example: action="get_security_recommendations",
                   parameters={"cluster_name": "my-cluster", "severity_filter": "High", "limit": 5}

        ### 6. check_compliance_status
        Check compliance against security frameworks and standards
        - Required: cluster_name (Name of the ECS cluster)
        - Optional: region (AWS region, default: us-east-1),
                   compliance_framework (Framework: aws-foundational, pci-dss, hipaa, soc2)
        - Example: action="check_compliance_status",
                   parameters={"cluster_name": "my-cluster",
                              "compliance_framework": "aws-foundational"}

        ## Security Analysis Coverage:

        ### Network Security
        - VPC configuration and security groups
        - Load balancer security settings
        - Public IP assignments and internet exposure
        - Network access controls and segmentation

        ### Container Security
        - Container runtime security configurations
        - Image security and vulnerability scanning
        - Privileged containers and capabilities
        - Root filesystem and user permissions

        ### IAM Security
        - Task and execution role configurations
        - Principle of least privilege compliance
        - Cross-account access patterns
        - Service-linked role configurations

        ### Secrets Management
        - Hardcoded secrets detection
        - AWS Secrets Manager integration
        - Environment variable security
        - Credential exposure risks

        ### Monitoring & Logging
        - Container Insights configuration
        - CloudWatch logging setup
        - Audit trail completeness
        - Security event monitoring

        ### Compliance Frameworks
        - AWS Well-Architected Security Pillar
        - SOC 2 Type II requirements
        - PCI DSS standards
        - HIPAA compliance (where applicable)

        ## Quick Usage Examples:
        ```
        # List available clusters
        action: "list_clusters"
        parameters: {"region": "us-east-1"}

        # Quick security analysis
        action: "analyze_cluster_security"
        parameters: {"cluster_name": "my-production-cluster"}

        # Get high-priority security issues only
        action: "get_security_recommendations"
        parameters: {"cluster_name": "my-cluster", "severity_filter": "High", "limit": 5}

        # Generate executive security report
        action: "generate_security_report"
        parameters: {"cluster_name": "my-cluster", "format": "executive"}

        # Check AWS foundational security compliance
        action: "check_compliance_status"
        parameters: {"cluster_name": "my-cluster", "compliance_framework": "aws-foundational"}

        # Interactive cluster selection
        action: "select_cluster_for_analysis"
        parameters: {"analysis_type": "quick"}
        ```

        ## Resource Discovery:
        If you don't know your cluster names, start with:

        # List all clusters in your region
        ecs_security_analysis_tool(action="list_clusters", parameters={"region": "us-east-1"})

        # Interactive selection with guided analysis
        ecs_security_analysis_tool(action="select_cluster_for_analysis")

        Parameters:
            action: The security analysis action to perform (see available actions above)
            parameters: Action-specific parameters (see parameter specifications above)

        Returns:
            Comprehensive security analysis results with recommendations and remediation guidance
        """
        # Initialize default parameters if None
        if parameters is None:
            parameters = {}

        return await ecs_security_analysis_tool(action, parameters)

    # Define prompt groups for bulk registration
    prompt_groups = {
        "General ECS security analysis": [
            "analyze security",
            "security analysis",
            "check security",
            "security assessment",
            "security review",
            "security audit",
            "security scan",
        ],
        "Security vulnerabilities and issues": [
            "security vulnerabilities",
            "security issues",
            "security problems",
            "security risks",
            "security threats",
            "security weaknesses",
        ],
        "Container security": [
            "container security",
            "docker security",
            "image security",
            "container vulnerabilities",
            "container misconfigurations",
        ],
        "Network security": [
            "network security",
            "vpc security",
            "security groups",
            "network vulnerabilities",
            "network misconfigurations",
        ],
        "IAM and access security": [
            "iam security",
            "access control",
            "permissions review",
            "role security",
            "privilege escalation",
        ],
        "Compliance and standards": [
            "compliance check",
            "security compliance",
            "compliance status",
            "security standards",
            "compliance audit",
            "well architected",
            "pci compliance",
            "hipaa compliance",
            "soc2 compliance",
        ],
        "Security reports and recommendations": [
            "security report",
            "security recommendations",
            "security findings",
            "security summary",
            "security dashboard",
        ],
        "Secrets and credentials": [
            "secrets security",
            "credential security",
            "hardcoded secrets",
            "secrets management",
            "credential exposure",
        ],
        "Monitoring and logging security": [
            "security monitoring",
            "security logging",
            "audit logs",
            "security events",
            "monitoring security",
        ],
        "Generic security queries": [
            "is my cluster secure",
            "how secure is my cluster",
            "security posture",
            "security status",
            "security health",
            "security best practices",
        ],
    }

    # Register all prompts with bulk registration
    register_security_analysis_prompts(mcp, prompt_groups)
