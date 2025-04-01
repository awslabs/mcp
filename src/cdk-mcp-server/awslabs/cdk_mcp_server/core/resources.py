"""AWS CDK MCP resource handlers."""

import logging
from awslabs.cdk_mcp_server.data.cdk_nag_parser import get_errors, get_rule_pack, get_warnings
from awslabs.cdk_mcp_server.data.genai_cdk_loader import (
    get_genai_cdk_construct,
    get_genai_cdk_construct_section,
    get_genai_cdk_overview,
    list_available_sections,
)
from awslabs.cdk_mcp_server.data.lambda_powertools_loader import get_lambda_powertools_section
from awslabs.cdk_mcp_server.data.solutions_constructs_parser import get_pattern_raw
from enum import Enum


# Set up logging
logger = logging.getLogger(__name__)


class RulePack(str, Enum):
    """CDK Nag rule packs."""

    AWS_SOLUTIONS = 'AWS Solutions'
    HIPAA_SECURITY = 'HIPAA Security'
    NIST_800_53_REV4 = 'NIST 800-53 rev 4'
    NIST_800_53_REV5 = 'NIST 800-53 rev 5'
    PCI_DSS_321 = 'PCI DSS 3.2.1'


async def get_all_cdk_nag_rules(rule_pack: str) -> str:
    """Get all rules for a specific CDK Nag rule pack.

    Args:
        rule_pack: The CDK Nag rule pack name (e.g., "AWS Solutions", "HIPAA Security")

    Returns:
        String containing the rule description and details
    """
    # Convert string to enum value
    try:
        rule_pack_enum = RulePack(rule_pack)
        return await get_rule_pack(rule_pack_enum)
    except ValueError:
        return f'Invalid rule pack: {rule_pack}. Valid values are: {", ".join([p.value for p in RulePack])}'


async def get_cdk_nag_warnings(rule_pack: str) -> str:
    """Get only the warnings section for a specific CDK Nag rule pack.

    Args:
        rule_pack: The CDK Nag rule pack name (e.g., "AWS Solutions", "HIPAA Security")

    Returns:
        String containing the warnings section of the rule pack
    """
    # Convert string to enum value
    try:
        rule_pack_enum = RulePack(rule_pack)
        return await get_warnings(rule_pack_enum)
    except ValueError:
        return f'Invalid rule pack: {rule_pack}. Valid values are: {", ".join([p.value for p in RulePack])}'


async def get_cdk_nag_errors(rule_pack: str) -> str:
    """Get only the errors section for a specific CDK Nag rule pack.

    Args:
        rule_pack: The CDK Nag rule pack name (e.g., "AWS Solutions", "HIPAA Security")

    Returns:
        String containing the errors section of the rule pack
    """
    # Convert string to enum value
    try:
        rule_pack_enum = RulePack(rule_pack)
        return await get_errors(rule_pack_enum)
    except ValueError:
        return f'Invalid rule pack: {rule_pack}. Valid values are: {", ".join([p.value for p in RulePack])}'


async def get_lambda_powertools_guidance(topic: str = '') -> str:
    """Get Lambda Powertools guidance on a specific topic.

    Lambda Powertools provides three core capabilities:
    - Structured Logging: Transform text logs into JSON objects with consistent fields
    - Tracing: Gain visibility into request flows across distributed services
    - Metrics: Collect quantitative data about your application's behavior

    Available topics:
    - logging: Structured logging implementation
    - tracing: Tracing implementation
    - metrics: Metrics implementation
    - cdk: CDK integration patterns
    - dependencies: Dependencies management
    - insights: Lambda Insights integration
    - bedrock: Bedrock Agent integration

    Args:
        topic: Topic to get guidance on

    Returns:
        String containing the guidance for the specified topic
    """
    return get_lambda_powertools_section(topic)


async def get_lambda_powertools_index() -> str:
    """Get Lambda Powertools guidance overview.

    Lambda Powertools provides three core capabilities:
    - Structured Logging: Transform text logs into JSON objects with consistent fields
    - Tracing: Gain visibility into request flows across distributed services
    - Metrics: Collect quantitative data about your application's behavior

    Available topics:
    - logging: Structured logging implementation
    - tracing: Tracing implementation
    - metrics: Metrics implementation
    - cdk: CDK integration patterns
    - dependencies: Dependencies management
    - insights: Lambda Insights integration
    - bedrock: Bedrock Agent integration

    Returns:
        String containing the Lambda Powertools guidance overview
    """
    return get_lambda_powertools_section('index')


async def get_solutions_construct_pattern_resource(pattern_name: str) -> str:
    """Get complete documentation for an AWS Solutions Constructs pattern.

    This resource returns the full documentation for a pattern including:
    - Code examples in multiple languages (TypeScript, Python, Java)
    - Props tables with all configuration options
    - Pattern properties and default settings
    - Architecture diagrams

    Common pattern categories include:
    - Serverless API (aws-apigateway-lambda, aws-apigateway-lambda-dynamodb)
    - Event-Driven (aws-s3-lambda, aws-sns-lambda, aws-sqs-lambda)
    - Storage (aws-s3-dynamodb, aws-kinesisfirehose-s3)
    - Web Application (aws-cloudfront-s3, aws-cloudfront-apigateway)

    Integration with other best practices:
    - Solutions Constructs implement many security best practices by default
    - They work well with Lambda Powertools for observability
    - They reduce the number of CDK Nag warnings in your code

    Args:
        pattern_name: The name of the pattern (e.g., 'aws-lambda-dynamodb')

    Returns:
        String containing the complete pattern documentation as markdown
    """
    # Get the raw pattern documentation directly
    pattern_raw = await get_pattern_raw(pattern_name)

    if 'error' in pattern_raw:
        from awslabs.cdk_mcp_server.data.solutions_constructs_parser import fetch_pattern_list

        return f"Pattern '{pattern_name}' not found. Available patterns: {', '.join(await fetch_pattern_list())}"

    # Return the raw content directly
    return pattern_raw['content']


async def get_genai_cdk_construct_section_resource(
    construct_type: str, construct_name: str, section: str
) -> str:
    """Get a specific section of documentation for a GenAI CDK construct.

    Example URIs:
    - genai-cdk-constructs://bedrock/agent/actiongroups
    - genai-cdk-constructs://bedrock/agent/alias
    - genai-cdk-constructs://bedrock/knowledgebases/chunking

    Args:
        construct_type: Type of the construct (e.g., 'bedrock')
        construct_name: Name of the construct (e.g., 'agent', 'knowledgebases')
        section: Section of the documentation (e.g., 'actiongroups', 'chunking')

    Returns:
        String containing the requested section of documentation
    """
    return get_genai_cdk_construct_section(construct_type, construct_name, section)


async def get_genai_cdk_construct_nested_section_resource(
    construct_type: str, construct_name: str, parent: str, child: str
) -> str:
    """Get a nested section of documentation for a GenAI CDK construct.

    Example URIs:
    - genai-cdk-constructs://bedrock/knowledgebases/vector/opensearch
    - genai-cdk-constructs://bedrock/knowledgebases/vector/aurora

    Args:
        construct_type: Type of the construct (e.g., 'bedrock')
        construct_name: Name of the construct (e.g., 'knowledgebases')
        parent: Parent section (e.g., 'vector')
        child: Child section (e.g., 'opensearch')

    Returns:
        String containing the requested nested section of documentation
    """
    section = f'{parent}/{child}'
    return get_genai_cdk_construct_section(construct_type, construct_name, section)


async def get_available_sections_resource(construct_type: str, construct_name: str) -> str:
    """Get available sections for a specific construct.

    Example URI:
    - genai-cdk-constructs://bedrock/agent/sections
    - genai-cdk-constructs://bedrock/knowledgebases/sections

    Args:
        construct_type: Type of the construct (e.g., 'bedrock')
        construct_name: Name of the construct (e.g., 'agent', 'knowledgebases')

    Returns:
        String containing available sections in markdown format
    """
    sections = list_available_sections(construct_type, construct_name)

    if not sections:
        return f'No sections found for {construct_name} in {construct_type}.'

    result = f'# Available Sections for {construct_name.capitalize()} in {construct_type.capitalize()}\n\n'

    for section in sorted(sections):
        result += (
            f'- [{section}](genai-cdk-constructs://{construct_type}/{construct_name}/{section})\n'
        )

    return result


async def get_genai_cdk_construct_resource(construct_type: str, construct_name: str) -> str:
    """Get essential information about a GenAI CDK construct.

    Example URIs:
    - genai-cdk-constructs://bedrock/Agent
    - genai-cdk-constructs://bedrock/KnowledgeBase

    Args:
        construct_type: Type of the construct (e.g., 'bedrock')
        construct_name: Name of the construct (e.g., 'Agent', 'KnowledgeBase')

    Returns:
        String containing formatted properties and code examples in markdown
    """
    return get_genai_cdk_construct(construct_type, construct_name)


async def get_genai_cdk_overview_resource(construct_type: str) -> str:
    """Get overview of a GenAI CDK construct type.

    Example URIs:
    - genai-cdk-constructs://bedrock
    - genai-cdk-constructs://opensearchserverless
    - genai-cdk-constructs://opensearch-vectorindex

    Args:
        construct_type: Type of the construct (e.g., 'bedrock')

    Returns:
        String containing overview documentation in markdown
    """
    return get_genai_cdk_overview(construct_type)
