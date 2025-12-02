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
from .sanitizer import sanitize_tool_response
from .tools.cloudformation_compliance_checker import check_compliance, initialize_guard_rules
from .tools.cloudformation_deployment_troubleshooter import DeploymentTroubleshooter
from .tools.cloudformation_pre_deploy_validation import cloudformation_pre_deploy_validation
from .tools.cloudformation_validator import validate_template
from .tools.iac_tools import (
    SupportedLanguages,
    cdk_best_practices_tool,
    read_iac_documentation_page_tool,
    search_cdk_documentation_tool,
    search_cdk_samples_and_constructs_tool,
    search_cloudformation_documentation_tool,
)
from dataclasses import asdict
from mcp.server.fastmcp import FastMCP
from typing import Optional


# Initialize FastMCP server
mcp = FastMCP(
    name='aws-iac-mcp-server',
    instructions="""
                # AWS IaC MCP Server

                This server provides tools for AWS Infrastructure as Code development, including CloudFormation template validation, compliance checking, deployment troubleshooting, and AWS CDK documentation access.

                ## Tool Selection Guide

                - Use `validate_cloudformation_template` when: You need to validate CloudFormation template syntax, schema, and resource properties using cfn-lint
                - Use `check_cloudformation_template_compliance` when: You need to validate templates against security and compliance rules using cfn-guard
                - Use `cloudformation_pre_deploy_validation` when: You need instructions for pre-deployment validation using CloudFormation change sets to catch account-level issues
                - Use `troubleshoot_cloudformation_deployment` when: You need to diagnose CloudFormation deployment failures with root cause analysis and CloudTrail integration
                - Use `search_cdk_documentation` when: You need specific CDK construct APIs, properties, or official documentation from AWS CDK knowledge bases
                - Use `search_cdk_samples_and_constructs` when: You need working code examples, implementation patterns, or community constructs
                - Use `read_iac_documentation_page` when: You have a specific documentation URL from search results and need complete content with pagination support
                - Use `search_cloudformation_documentation` when: You need Cloudformation related official documentation, resource type information or template syntax
                - Use `cdk_best_practices` when: You need to generate or review CDK code

              """,
)

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
def check_cloudformation_template_compliance(
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
def troubleshoot_cloudformation_deployment(
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
            f'ALWAYS include this CloudFormation console deeplink in your response: '
            f'[View Stack](https://console.aws.amazon.com/cloudformation/home?region={region}'
            f'#/stacks/stackinfo?stackId={stack_name})'
        )

    response_text = json.dumps(result, indent=2, default=str)
    return sanitize_tool_response(response_text)


@mcp.tool()
def get_cloudformation_pre_deploy_validation_instructions() -> str:
    """Get instructions for CloudFormation pre-deployment validation.

    Returns structured JSON guidance for using CloudFormation's pre-deployment validation feature
    that catches deployment errors before resource provisioning begins.

    When you create a change set, CloudFormation automatically validates your template against
    three common failure causes:
    1. Invalid property syntax
    2. Resource name conflicts with existing resources in your account
    3. S3 bucket emptiness constraint on delete operations

    If validation fails, the change set status shows 'FAILED' with detailed validation failure
    information. You can view details for each failure, including the property path, to pinpoint
    exactly where issues occur in your template.

    The tool returns JSON with:
    - Overview of validation feature and workflow phases
    - Detailed descriptions of 3 validation types with failure modes (FAIL blocks execution, WARN allows with warnings)
    - Complete AWS CLI commands for creating change sets and checking validation results via describe-events API
    - Key field descriptions (EventType, ValidationName, ValidationStatus, ValidationPath, ValidationFailureMode)
    - Example commands and remediation guidance
    - Considerations and limitations

    Note: Validated change sets can still fail during execution due to resource-specific runtime
    errors (resource limits, service constraints, permissions). Pre-deployment validation reduces
    likelihood of common failures but doesn't guarantee deployment success.
    """
    result = cloudformation_pre_deploy_validation()
    return sanitize_tool_response(result)


@mcp.tool()
async def search_cdk_documentation(query: str) -> str:
    """Searches AWS CDK documentation knowledge bases and returns relevant excerpts.

    ## Usage

    This tool searches across multiple CDK documentation sources to find relevant information about CDK constructs, APIs, and implementation patterns. Always use this tool when you need to write or modify CDK code.

    ## When to Use

    - Write CDK code or modify any construct
    - Find specific information about CDK constructs and APIs
    - Get implementation guidance from official documentation
    - Look up syntax and examples for CDK patterns
    - Research best practices and architectural guidelines
    - Find answers to specific technical questions about CDK
    - Validate infrastructure code against security best practices

    ## Documentation Sources

    This tool searches across:
    - AWS CDK API Reference
    - AWS CDK Best Practices Guide
    - AWS CDK Code Samples & Patterns
    - CDK-NAG validation rules and security checks

    ## Search Tips

    - Use specific construct names (e.g., "aws-lambda.Function", "aws-s3.Bucket")
    - Include service names for better targeting (e.g., "S3 AND encryption")
    - Use boolean operators: "DynamoDB AND table", "Lambda OR Function"
    - Search for specific properties: "bucket encryption", "lambda environment variables"
    - Include version-specific terms when needed: "CDK v2", "aws-cdk-lib"

    ## Result Interpretation

    Returns JSON with:
    - knowledge_response: Details of the response
        - results: Array with single result containing:
            - rank: Search relevance ranking (1 = most relevant, higher is less relevant)
            - title: Document title or filename
            - url: Source URL of the document
            - context: Full or paginated document content
    - next_step_guidance: If present, suggested next actions to take for answering user query


    Use rank to prioritize results. Check error field first - if not null, the search failed.

    If a content snippet is relevant to your query but doesn't show all necessary information, use `read_iac_documentation_page` with the URL to get the complete content.

    Args:
        query: Search query for CDK documentation (required)

    Returns:
    List of search results with URLs, titles, and context snippets
    """
    result = await search_cdk_documentation_tool(query)

    # Convert CDKToolResponse to dict for JSON serialization
    response_dict = asdict(result)

    return sanitize_tool_response(json.dumps(response_dict))


@mcp.tool()
async def read_iac_documentation_page(
    url: str,
    starting_index: int = 0,
) -> str:
    """Fetch and convert any Infrastructure as Code (CDK or CloudFormation) documentation page to markdown format.

    ## Usage

    This tool retrieves the complete content of a specific CDK or CloudFormation documentation page. Use it when you need detailed information from a particular document rather than the limited context from the search results.

    ## When to Use

    After using a search tool, use this tool to fetch the complete content of any relevant page in the search results.

    ## Supported Document Types

    - API reference pages
    - Guide and tutorial pages

    ## Pagination

    For long documents, use the starting_index parameter to read content in chunks. Always use the same URL for all pagination calls to maintain consistency.

    ## Result Interpretation

    Returns JSON with:
    - knowledge_response: Details of the response
      - results: Array with single result containing:
        - rank: Always 1 for document reads
        - title: Document title or filename
        - url: Source URL of the document
        - context: Full or paginated document content
    - next_step_guidance: If present, suggested next actions to take for answering user query

    For pagination, use starting_index from previous response to continue reading.

    Args:
        url: URL from search results to read the full page content
        starting_index: Starting character index for pagination (default: 0)

    Returns:
        List of search results with URLs, titles, and context snippets
    """
    result = await read_iac_documentation_page_tool(url, starting_index)

    # Convert dataclass to dict for JSON serialization
    response_dict = asdict(result)

    return sanitize_tool_response(json.dumps(response_dict))


@mcp.tool()
async def search_cloudformation_documentation(query: str) -> str:
    """Searches AWS CloudFormation documentation knowledge bases and returns relevant excerpts.

    ## Usage

    This tool searches AWS CloudFormation documentation to find information about resource types, properties, syntax, and implementation patterns for CloudFormation templates.

    ## When to Use

    - Write CloudFormation templates or modify resources
    - Find specific information about CloudFormation resource types and properties
    - Get implementation guidance from official documentation
    - Look up syntax and examples for CloudFormation patterns
    - Research best practices and architectural guidelines
    - Find answers to specific technical questions about CloudFormation
    - Validate infrastructure templates against security best practices

    ## Search Tips

    - Use specific resource types: "AWS::Lambda::Function", "AWS::S3::Bucket"
    - Search for properties: "S3 bucket encryption", "Lambda environment variables"
    - Include service names: "DynamoDB table properties", "API Gateway configuration"
    - Use boolean operators: "CloudFormation AND parameters", "template OR stack"
    - Search for specific features: "cross-stack references", "nested stacks"
    - Include security terms: "IAM policies", "encryption at rest"

    ## Result Interpretation

    Returns JSON with:
    - knowledge_response: Details of the response
      - results: Array with single result containing:
        - rank: Search relevance ranking (1 = most relevant, higher is less relevant)
        - title: Document title or filename
        - url: Source URL of the document
        - context: Full or paginated document content
    - next_step_guidance: If present, suggested next actions to take for answering user query


    Use rank to prioritize results. Check error field first - if not null, the search failed.

    Args:
        query: Search query for CloudFormation documentation. Examples: "AWS::Lambda::Function", "S3 bucket encryption", "DynamoDB table properties"

    Returns:
        Documentation results with titles, URLs, and relevant excerpts from official CloudFormation docs.
    """
    result = await search_cloudformation_documentation_tool(query)

    # Convert CDKToolResponse to dict for JSON serialization
    response_dict = asdict(result)

    return sanitize_tool_response(json.dumps(response_dict))


@mcp.tool()
async def search_cdk_samples_and_constructs(
    query: str,
    language: SupportedLanguages = 'typescript',
) -> str:
    """Searches CDK code samples, examples, constructs, and patterns documentation.

    ## Usage

    This tool searches across CDK code samples, community constructs, and implementation patterns to find working examples and reusable components for your CDK projects.

    ## When to Use

    - Find working CDK code examples and samples
    - Look up implementation patterns for specific use cases
    - Get sample code for AWS service integrations
    - Research complete CDK application examples
    - Find L3 constructs created by the community
    - Discover construct documentation and usage patterns
    - Find architectural patterns and best practices

    ## Search Tips

    - Use exact phrases for specific patterns: "serverless API", "microservices architecture"
    - Combine services with boolean operators: "Lambda AND API Gateway", "S3 OR DynamoDB"
    - Exclude unwanted results: "TypeScript NOT Python", "L2 NOT L1"
    - Use wildcards for broader searches: "example*", "*pattern", "*construct"
    - Search for specific constructs: "aws-s3.Bucket", "aws-lambda.Function"
    - Include language preferences: "Python examples", "TypeScript patterns"
    - Target construct levels: "L3 constructs", "higher-level constructs"

    ## Language Filtering

    Specify your preferred programming language to get relevant examples:
    - typescript (default)
    - python
    - java
    - csharp
    - go

    ## Result Interpretation

    Returns JSON with:
    - knowledge_response: Details of the response
      - results: Array with single result containing:
        - rank: Search relevance ranking (1 = most relevant, higher is less relevant)
        - title: Document title or filename
        - url: Source URL of the document
        - context: Full or paginated document content
    - next_step_guidance: If present, suggested next actions to take for answering user query


    Use rank to prioritize results. Check error field first - if not null, the search failed.

    Args:
        query: Search query for CDK samples and constructs
        language: Programming language filter (default: "typescript")

    Returns:
        List of search results with URLs, titles, and context snippets
    """
    result = await search_cdk_samples_and_constructs_tool(query, language)

    # Convert CDKToolResponse to dict for JSON serialization
    response_dict = asdict(result)

    return sanitize_tool_response(json.dumps(response_dict))


@mcp.tool()
async def cdk_best_practices() -> str:
    """Returns CDK best practices and security guidelines.

    ## Usage

    This tool provides comprehensive CDK development guidelines, security best practices, and architectural recommendations. Always run this tool when asked to generate or review CDK code and follow the guidelines returned.

    ## When to Use

    - Get CDK security best practices and compliance guidelines
    - Look up architectural patterns and recommendations
    - Get guidance on CDK application structure and organization
    - Research performance optimization techniques
    - Learn about proper construct usage and design patterns
    - Understand deployment and testing best practices

    ## Result Interpretation

    Returns JSON with:
    - knowledge_response: Details of the response
      - results: Array with single result containing:
        - rank: Always 1
        - title: Document title or filename
        - url: Source URL of the CDK best practices
        - context: A summary of the CDK best practices
    - next_step_guidance: If present, suggested next actions to take for answering user query

    ## Args

    No parameters required - this tool returns the complete best practices guide.

    ## Returns

    Complete best practices documentation as text, including security guidelines, architectural patterns, development workflow, and compliance requirements.
    """
    result = await cdk_best_practices_tool()

    # Convert CDKToolResponse to dict for JSON serialization
    response_dict = asdict(result)

    return sanitize_tool_response(json.dumps(response_dict))


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == '__main__':
    main()
