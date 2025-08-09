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

"""Unified API for Infrastructure-as-Code Network Firewall analysis."""

import json
from typing import Optional, Dict, List, Any
from typing_extensions import TypedDict

from .iac_parser_factory import get_parser_factory
from .network_firewall import (
    analyze_terraform_network_firewall_policy,
    analyze_cdk_network_firewall_policy,
    analyze_cloudformation_network_firewall_policy,
    simulate_terraform_firewall_traffic,
    simulate_cdk_firewall_traffic,
    simulate_cloudformation_firewall_traffic,
)
from ..utils.logger import get_logger
from ..utils.response_formatter import format_response
from ..utils.circuit_breaker import aws_api_circuit_breaker
from ..utils.metrics import track_iac_operation
from ..server import mcp

logger = get_logger(__name__)


class AnalysisResult(TypedDict):
    """Typed result for firewall policy analysis."""

    format_detected: str
    policy_summary: Dict[str, Any]
    security_assessment: Dict[str, Any]
    traffic_analysis: Dict[str, Any]
    recommendations: List[Dict[str, str]]
    original_analysis: Dict[str, Any]


@mcp.tool(name="analyze_iac_firewall_policy")
@aws_api_circuit_breaker("networkfirewall", "analyze_iac_policy")
@track_iac_operation("analyze_policy")
def analyze_iac_firewall_policy(
    content: str,
    format_hint: Optional[str] = None,
    compare_with_aws: Optional[str] = None,
    include_traffic_simulation: bool = True,
) -> str:
    """Unified entry point for analyzing Network Firewall policies in any IaC format.

    This tool automatically detects the IaC format (Terraform, CDK, CloudFormation)
    and provides comprehensive analysis of the firewall policy.

    Args:
        content: The IaC content defining the firewall policy
        format_hint: Optional hint for format type ("terraform", "cdk", "cloudformation")
        compare_with_aws: Optional firewall ARN to compare against deployed resource
        include_traffic_simulation: Whether to include traffic flow analysis

    Returns:
        JSON string with comprehensive policy analysis
    """
    try:
        # Get appropriate parser using factory
        factory = get_parser_factory()
        parser = factory.get_parser(format_name=format_hint, content=content)

        # Validate syntax first
        validation_result = parser.validate_syntax(content)
        if not validation_result.get("valid", False):
            return format_response(
                success=False,
                error=f"Invalid {validation_result.get('format', 'IaC')} syntax: {validation_result.get('errors', ['Unknown error'])}",
            )

        detected_format = validation_result.get("format", "unknown")
        logger.info(f"Detected IaC format: {detected_format}")

        # Route to appropriate analysis function based on detected format
        if detected_format == "terraform":
            analysis_result = analyze_terraform_network_firewall_policy(content, compare_with_aws)
        elif detected_format == "cdk":
            analysis_result = analyze_cdk_network_firewall_policy(content, compare_with_aws)
        elif detected_format == "cloudformation":
            analysis_result = analyze_cloudformation_network_firewall_policy(content, compare_with_aws)
        else:
            return format_response(success=False, error=f"Unsupported IaC format: {detected_format}")

        # Parse the analysis result
        original_analysis = json.loads(analysis_result)
        if original_analysis.get("status") != "success":
            return analysis_result  # Return original error

        # Extract data from original analysis
        analysis_data = original_analysis.get("data", {})
        format_analysis_key = f"{detected_format}_analysis"
        format_analysis = analysis_data.get(format_analysis_key, {})

        # Build unified result structure
        result: AnalysisResult = {
            "format_detected": detected_format,
            "policy_summary": {
                "name": format_analysis.get("policy_name", "unknown"),
                "total_rules": format_analysis.get("total_rules", 0),
                "stateless_config": format_analysis.get("stateless_config", {}),
                "stateful_config": format_analysis.get("stateful_config", {}),
                "rules_by_type": format_analysis.get("rules_by_type", {}),
                "rules_by_format": format_analysis.get("rules_by_format", {}),
            },
            "security_assessment": analysis_data.get("security_assessment", {}),
            "traffic_analysis": analysis_data.get("traffic_analysis", {}),
            "recommendations": _generate_enhanced_recommendations(analysis_data, detected_format),
            "original_analysis": analysis_data,
        }

        # Add AWS comparison if available
        if compare_with_aws and "aws_comparison" in analysis_data:
            result["aws_comparison"] = analysis_data["aws_comparison"]

        return format_response(success=True, data=result)

    except Exception as e:
        logger.error(f"Failed to analyze IaC firewall policy: {str(e)}")
        return format_response(success=False, error=f"Analysis failed: {str(e)}")


def _generate_enhanced_recommendations(analysis_data: Dict[str, Any], format_type: str) -> List[Dict[str, str]]:
    """Generate enhanced recommendations based on comprehensive analysis."""
    recommendations = []

    security_assessment = analysis_data.get("security_assessment", {})
    traffic_analysis = analysis_data.get("traffic_analysis", {})

    # Security posture recommendations
    if traffic_analysis.get("security_posture") == "default_allow":
        recommendations.append(
            {
                "priority": "HIGH",
                "category": "SECURITY",
                "recommendation": "Implement default-deny security posture",
                "rationale": "Default-deny provides better security baseline and reduces attack surface",
                "format_specific": f"In {format_type}, set stateful_default_actions to 'aws:drop_strict'",
            }
        )

    # Rule coverage recommendations
    format_analysis_key = f"{format_type}_analysis"
    format_analysis = analysis_data.get(format_analysis_key, {})
    rules_by_type = format_analysis.get("rules_by_type", {})

    if rules_by_type.get("stateful", 0) == 0:
        recommendations.append(
            {
                "priority": "MEDIUM",
                "category": "INSPECTION",
                "recommendation": "Add stateful rules for deep packet inspection",
                "rationale": "Stateful rules enable L7 application-layer inspection and protocol validation",
                "format_specific": f"In {format_type}, add stateful rule groups with Suricata or native rules",
            }
        )

    if rules_by_type.get("stateless", 0) == 0:
        recommendations.append(
            {
                "priority": "LOW",
                "category": "PERFORMANCE",
                "recommendation": "Consider adding stateless rules for performance optimization",
                "rationale": "Stateless rules can block obvious threats before expensive stateful processing",
                "format_specific": f"In {format_type}, add high-priority stateless rules for known bad IPs",
            }
        )

    # Security level recommendations
    security_level = security_assessment.get("security_level", "unknown")
    if security_level == "low":
        recommendations.append(
            {
                "priority": "HIGH",
                "category": "SECURITY",
                "recommendation": "Address multiple security risks identified in analysis",
                "rationale": "Current configuration has significant security gaps",
                "format_specific": f"Review {format_type} configuration for permissive rules and weak defaults",
            }
        )

    # Format-specific recommendations
    if format_type == "terraform" and format_analysis.get("total_rules", 0) > 100:
        recommendations.append(
            {
                "priority": "LOW",
                "category": "MAINTAINABILITY",
                "recommendation": "Consider splitting large policy into multiple modules",
                "rationale": "Large Terraform configurations become difficult to maintain and review",
                "format_specific": "Use Terraform modules to organize rule groups by function",
            }
        )

    if format_type == "cloudformation":
        rules_by_format = format_analysis.get("rules_by_format", {})
        if rules_by_format.get("rules_source_list", 0) > 0:
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "category": "PERFORMANCE",
                    "recommendation": "Domain-based filtering detected - ensure regular updates",
                    "rationale": "RulesSourceList requires periodic updates to maintain effectiveness",
                    "format_specific": "Implement automation to update allowed/blocked domain lists",
                }
            )

    return recommendations


@mcp.tool(name="simulate_iac_firewall_traffic")
@aws_api_circuit_breaker("networkfirewall", "simulate_traffic")
@track_iac_operation("simulate_traffic")
def simulate_iac_firewall_traffic(content: str, test_flows: str, format_hint: Optional[str] = None) -> str:
    """Simulate traffic flows against IaC firewall policy.

    Args:
        content: The IaC content defining the firewall policy
        test_flows: JSON string containing array of traffic flows to test
        format_hint: Optional hint for format type

    Returns:
        JSON string with simulation results
    """
    try:
        # Auto-detect format if not provided
        factory = get_parser_factory()
        parser = factory.get_parser(format_name=format_hint, content=content)

        validation_result = parser.validate_syntax(content)
        if not validation_result.get("valid", False):
            return format_response(success=False, error=f"Invalid {validation_result.get('format', 'IaC')} syntax")

        detected_format = validation_result.get("format", "unknown")

        # Route to appropriate simulation function
        if detected_format == "terraform":
            return simulate_terraform_firewall_traffic(content, test_flows)
        elif detected_format == "cdk":
            return simulate_cdk_firewall_traffic(content, test_flows)
        elif detected_format == "cloudformation":
            return simulate_cloudformation_firewall_traffic(content, test_flows)
        else:
            return format_response(success=False, error=f"Unsupported format for traffic simulation: {detected_format}")

    except Exception as e:
        logger.error(f"Traffic simulation failed: {str(e)}")
        return format_response(success=False, error=f"Simulation failed: {str(e)}")


@mcp.tool(name="validate_iac_firewall_syntax")
@track_iac_operation("validate_syntax")
def validate_iac_firewall_syntax(content: str, format_hint: Optional[str] = None) -> str:
    """Validate IaC firewall policy syntax.

    Args:
        content: The IaC content to validate
        format_hint: Optional hint for format type

    Returns:
        JSON string with validation results
    """
    try:
        factory = get_parser_factory()
        parser = factory.get_parser(format_name=format_hint, content=content)

        validation_result = parser.validate_syntax(content)

        return format_response(success=True, data=validation_result)

    except Exception as e:
        logger.error(f"Syntax validation failed: {str(e)}")
        return format_response(success=False, error=f"Validation failed: {str(e)}")
