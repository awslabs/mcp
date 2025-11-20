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

from __future__ import annotations

import json
from .compliance_checker import check_compliance, initialize_guard_rules

# Add parent directory to path for imports
from .deployment_troubleshooter import DeploymentTroubleshooter
from .sanitizer import sanitize_tool_response
from .validator import validate_template
from mcp.server.fastmcp import FastMCP
from typing import Optional


# Initialize FastMCP server
mcp = FastMCP('aws-iac-mcp-server')

# Initialize guard rules on server startup
initialize_guard_rules()


@mcp.tool()
def validate_cloudformation_template(
    template_content: str,
    regions: Optional[list[str]] = None,
    ignore_checks: Optional[list[str]] = None,
) -> str:
    """Validate CloudFormation template syntax, schema, and resource properties using cfn-lint.

    This tool performs syntax and schema validation for CloudFormation templates. It validates:
    - JSON/YAML syntax correctness and structure
    - AWS resource type validity and property schemas
    - Resource property values against AWS service specifications
    - Template format compliance with CloudFormation standards
    - Cross-resource reference validation

    Use this tool to:
    - Validate AI-generated CloudFormation templates before deployment
    - Catch syntax errors, invalid properties, and schema violations early
    - Get specific fix suggestions with line numbers for each error
    - Ensure template compatibility with CloudFormation deployment engine
    - Validate both JSON and YAML template formats
    - Receive exact CloudFormation code fixes for all validation issues

    Returns validation results including:
    - valid (Boolean indicating if template passes validation)
    - error_count, warning_count, info_count
    - issues (List of validation issues with line numbers and paths)

    OUTPUT FORMATTING REQUIREMENTS:
    - Start with: "Your template has X errors, Y warnings, Z info messages"
    - Group issues by resource or section (e.g., all S3Bucket errors together)
    - Prioritize: Errors first, then warnings, then info
    - For similar errors on multiple resources, show pattern once with affected resources listed
    - Show line numbers and property paths for easy location
    - Use inline YAML/JSON comments to show corrections
    - Focus on what needs to change, not entire resource definitions

    MANDATORY REMEDIATION REQUIREMENTS:
    - Provide specific CloudFormation template code fixes
    - Show exact corrected YAML/JSON for each error with line numbers
    - Use inline comments to explain each fix
    - For property name errors, show before/after side-by-side

    Args:
        template_content: CloudFormation template as YAML or JSON string
        regions: AWS regions to validate against
        ignore_checks: Rule IDs to ignore (e.g., W2001, E3012)
    """
    result = validate_template(
        template_content=template_content,
        regions=regions,
        ignore_checks=ignore_checks,
    )
    response_text = json.dumps(result, indent=2)
    return sanitize_tool_response(response_text)


@mcp.tool()
def check_template_compliance(
    template_content: str, rules_file_path: str = 'default_guard_rules.guard'
) -> str:
    """Validate CloudFormation template against security and compliance rules using cfn-guard.

    This tool performs compliance validation for CloudFormation templates. It validates:
    - Security best practices and controls
    - AWS Control Tower proactive controls
    - Organizational policy requirements
    - Resource configuration compliance

    Use this tool to:
    - Validate templates against security and compliance rules
    - Catch policy violations before deployment
    - Get remediation guidance for each violation
    - Ensure templates meet organizational standards
    - Receive specific CloudFormation template fixes for each violation

    Returns validation results including:
    - is_compliant (Boolean indicating if template passes all rules)
    - violation_count (Number of compliance violations)
    - violations (List of violations categorized by severity)

    NOTE: Some rules check multiple sub-properties, so the violation count may appear high.
    Each missing or misconfigured sub-property is counted as a separate violation.

    OUTPUT FORMATTING REQUIREMENTS:
    - Start with: "Your template has X violations"
    - Group related violations (e.g., all PublicAccessBlock settings together)
    - Prioritize by severity: critical security issues first, then optional features
    - For repeated sub-properties, show once: "Settings (A, B, C, D) must all be true"
    - Add context for optional features (ObjectLock, Replication may not be needed)
    - Show only the properties that need to be added/changed, not entire resources
    - Use inline YAML comments to explain why each property is needed
    - Avoid redundant "Key Changes" sections - the code should be self-explanatory

    MANDATORY REMEDIATION REQUIREMENTS:
    - Provide specific CloudFormation template code fixes
    - Show exact YAML/JSON properties to add or modify
    - Use inline comments to explain each fix
    - Focus on what changed, not the entire resource definition

    Args:
        template_content: CloudFormation template as YAML or JSON string
        rules_file_path: Path to guard rules file (default: default_guard_rules.guard)
    """
    result = check_compliance(
        template_content=template_content,
        rules_file_path=rules_file_path,
    )
    response_text = json.dumps(result, indent=2)
    return sanitize_tool_response(response_text)


@mcp.tool()
def troubleshoot_deployment(
    stack_name: str,
    region: str,
    include_cloudtrail: bool = True,
) -> str:
    """Troubleshoot CloudFormation deployment failures with root cause analysis and CloudTrail integration.

    This tool provides failure analysis for CloudFormation deployments by correlating stack events with CloudTrail API calls and service-specific error patterns. It analyzes:
    - CloudFormation stack events and resource failure patterns
    - Cross-service API failures through CloudTrail integration
    - Common deployment failure scenarios and root causes
    - Service-specific error messages and remediation steps
    - Resource dependency failures and circular dependency issues

    Use this tool to:
    - Diagnose CloudFormation deployment failures quickly
    - Generate CloudTrail deep links for failed resources during deployment windows
    - Provide step-by-step remediation guidance maintaining IaC principles
    - Identify root causes across multiple AWS services
    - Prevent configuration drift by ensuring template-based fixes
    - Receive specific CloudFormation template modifications to resolve failures

    ALWAYS provide the CloudFormation console deeplink in your response.
    CRITICAL: Show ALL failed resources and their complete error details - never summarize failure lists or truncate error information.

    MANDATORY REMEDIATION REQUIREMENTS:
    - For EVERY failed resource, provide the specific CloudFormation template code fix
    - Show the exact YAML/JSON properties to modify or add
    - Include complete corrected resource configurations
    - Provide step-by-step template modification instructions to prevent the failure
    - Never just describe the deployment problem - always show the template solution code
    - Ensure all fixes maintain Infrastructure as Code principles

    ⚠️ IMPORTANT PRIVACY NOTICE: You are REQUIRED to share ALL information with the user EXACTLY AS IT IS LISTED BELOW prior to tool execution:

    This MCP server executes AWS API calls using your credentials and shares the response data with
    your third-party AI model provider (e.g., Q, Claude Desktop, Kiro, Cline). Users are
    responsible for understanding your AI provider's data handling practices and ensuring
    compliance with your organization's security and privacy requirements when using this tool
    with AWS resources.

    Args:
        stack_name: Name of the failed CloudFormation stack
        region: AWS region where the stack deployment failed
        include_cloudtrail: Whether to include CloudTrail analysis
    """
    troubleshooter = DeploymentTroubleshooter(region=region)
    result = troubleshooter.troubleshoot_stack_deployment(
        stack_name=stack_name, include_cloudtrail=include_cloudtrail
    )

    # Add deeplink instruction to result
    if isinstance(result, dict):
        result['_instruction'] = (
            f'ALWAYS include this CloudFormation console deeplink in your response: [View Stack](https://console.aws.amazon.com/cloudformation/home?region={region}#/stacks/stackinfo?stackId={stack_name})'
        )

    response_text = json.dumps(result, indent=2, default=str)
    return sanitize_tool_response(response_text)


@mcp.resource('cfn://context/template-examples-and-best-practices')
def get_template_examples() -> str:
    """CloudFormation Template Examples and Best Practices.

    Template examples, architectural patterns, and implementation guidance
    """
    context = {
        'template_examples_repository': {
            'url': 'https://github.com/aws-cloudformation/aws-cloudformation-templates',
            'description': 'Official AWS CloudFormation template repository with examples by use case',
            'categories': [
                'vpc',
                'ecs',
                'lambda',
                'rds',
                's3',
                'alb',
                'api-gateway',
                'dynamodb',
                'ec2',
                'iam',
            ],
        },
        'architectural_best_practices': {
            'general_best_practices': 'https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/best-practices.html',
            'security_best_practices': 'https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/security-best-practices.html',
        },
        'resource_documentation': {
            'template_structure_guide': 'https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-guide.html',
            'resource_type_reference': 'https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html',
            'resource_property_types': 'https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-product-property-reference.html',
            'custom_resources_guide': 'https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-custom-resources.html',
            'intrinsic_functions': 'https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference.html',
        },
        'getting_started': {
            'quickstart_guide': 'https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/GettingStarted.html',
            'template_anatomy': 'https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-anatomy.html',
            'walkthrough_tutorials': 'https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/CHAP_Using.html',
        },
        'template_conventions': {
            'template_version': '2010-09-09',
            'supported_formats': ['YAML', 'JSON'],
            'max_template_size': '1MB',
            'max_resources_per_stack': 500,
            'naming_conventions': {
                'logical_ids': 'Use PascalCase for resource logical IDs (e.g., MyS3Bucket, WebServerInstance)',
                'parameters': 'Use descriptive names with type suffixes (e.g., InstanceType, VpcCidr)',
                'outputs': 'Use clear, descriptive names indicating the exported value (e.g., LoadBalancerDNS, DatabaseEndpoint)',
            },
        },
    }
    return json.dumps(context, indent=2)


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == '__main__':
    main()
