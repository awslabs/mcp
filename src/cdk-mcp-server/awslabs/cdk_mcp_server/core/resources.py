# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""AWS CDK MCP resource handlers."""

import logging
from awslabs.cdk_mcp_server.data.cdk_nag_parser import get_errors, get_rule_pack, get_warnings
from awslabs.cdk_mcp_server.data.genai_cdk_loader import (
    get_section,
    list_sections,
    fetch_readme,
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
    - genai-cdk-constructs://bedrock/agents/actiongroups
    - genai-cdk-constructs://bedrock/agents/alias
    - genai-cdk-constructs://bedrock/knowledgebases/chunking

    Args:
        construct_type: Type of the construct (e.g., 'bedrock')
        construct_name: Name of the construct (e.g., 'agents', 'knowledgebases')
        section: Section of the documentation (e.g., 'actiongroups', 'chunking')

    Returns:
        String containing the requested section of documentation
    """
    # Fetch section from GitHub
    result = await get_section(construct_type, construct_name, section)
    
    if 'error' in result:
        return f"Error fetching section from GitHub: {result['error']}"
        
    return result['content']


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
    # First try to use parent as the section name and child as a subsection
    section = f'{parent}/{child}'
    result = await get_section(construct_type, construct_name, section)
    
    if 'error' not in result:
        return result['content']
        
    # If that fails, try as a combined section name
    section = f'{parent} {child}'
    result = await get_section(construct_type, construct_name, section)
    
    if 'error' in result:
        return f"Error fetching nested section from GitHub: {result['error']}"
        
    return result['content']


async def get_available_sections_resource(construct_type: str, construct_name: str) -> str:
    """Get available sections for a specific construct.

    Example URI:
    - genai-cdk-constructs://bedrock/agents/sections
    - genai-cdk-constructs://bedrock/knowledgebases/sections

    Args:
        construct_type: Type of the construct (e.g., 'bedrock')
        construct_name: Name of the construct (e.g., 'agents', 'knowledgebases')

    Returns:
        String containing available sections in markdown format
    """
    # Handle singular/plural conversion for agent
    if construct_name.lower() == 'agent':
        construct_name = 'agents'
        
    # List sections from GitHub
    result = await list_sections(construct_type, construct_name)
    
    if 'error' in result:
        return f"Error fetching sections from GitHub: {result['error']}"

    sections = result['sections']
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
    - genai-cdk-constructs://bedrock/Agents
    - genai-cdk-constructs://bedrock/KnowledgeBase
    - genai-cdk-constructs://bedrock/Amazon Bedrock Knowledge BasesVectorKnowledgeBase (from search results)

    Args:
        construct_type: Type of the construct (e.g., 'bedrock')
        construct_name: Name of the construct (e.g., 'Agent', 'KnowledgeBase')

    Returns:
        String containing formatted properties and code examples in markdown
    """
    from awslabs.cdk_mcp_server.data.genai_cdk_loader import fetch_readme as get_readme
    
    # Handle search result format (e.g., "Amazon Bedrock Knowledge BasesVectorKnowledgeBase")
    if construct_name.startswith("Amazon Bedrock Knowledge Bases"):
        # Extract the section name that comes after "Amazon Bedrock Knowledge Bases"
        # This is for the special case of knowledge-bases subdirectory in bedrock
        section_name = construct_name.replace("Amazon Bedrock Knowledge Bases", "").strip()
        if section_name:
            # Get the section from the knowledge-bases README
            result = await get_section('bedrock', 'knowledge-bases', section_name)
            if 'error' not in result:
                return result['content']
        
        # If no section specified or section not found, get the whole README
        result = await get_readme('bedrock', 'knowledge-bases')
        if 'error' not in result:
            return result['content']
    
    # Normalize construct name
    construct_name_lower = construct_name.lower()
    
    # If the construct is Agent, use agents for GitHub
    if construct_name_lower == 'agent':
        construct_name_lower = 'agents'
    
    # If it looks like a "knowledge base" reference, try the subdirectory
    if "knowledge" in construct_name_lower and "base" in construct_name_lower:
        result = await get_readme('bedrock', 'knowledge-bases')
        if 'error' not in result:
            return result['content']
    
    # Fetch the entire README from GitHub
    result = await get_readme(construct_type)
    
    if 'error' not in result:
        return result['content']
    
    # If that fails, try to fetch a specific construct README
    result = await get_readme(construct_type, construct_name_lower)
    
    if 'error' in result:
        return f"Error fetching construct from GitHub: {result['error']}"
    
    return result['content']


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
    from awslabs.cdk_mcp_server.data.genai_cdk_loader import fetch_readme as get_readme
    
    # Fetch README from GitHub
    result = await get_readme(construct_type)
    
    if 'error' in result:
        return f"Error fetching overview from GitHub: {result['error']}"
    
    return result['content']
