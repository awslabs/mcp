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

"""AWS CDK MCP tool handlers."""

import logging
import os
import re
from awslabs.cdk_mcp_server.core import search_utils
from awslabs.cdk_mcp_server.data.cdk_nag_parser import (
    check_cdk_nag_suppressions,
    get_rule,
)
from awslabs.cdk_mcp_server.data.genai_cdk_loader import (
    list_available_constructs,
)
from awslabs.cdk_mcp_server.data.schema_generator import generate_bedrock_schema_from_file
from awslabs.cdk_mcp_server.data.solutions_constructs_parser import (
    fetch_pattern_list,
    get_pattern_info,
    search_patterns,
)
from awslabs.cdk_mcp_server.static import (
    CDK_GENERAL_GUIDANCE,
)
from mcp.server.fastmcp import Context
from typing import Any, Dict, List, Optional


# Set up logging
logger = logging.getLogger(__name__)


async def cdk_guidance(
    ctx: Context,
) -> str:
    """Use this tool to get prescriptive CDK advice for building applications on AWS.

    Args:
        ctx: MCP context
    """
    return CDK_GENERAL_GUIDANCE


async def explain_cdk_nag_rule(
    ctx: Context,
    rule_id: str,
) -> Dict[str, Any]:
    """Explain a specific CDK Nag rule with AWS Well-Architected guidance.

    CDK Nag is a crucial tool for ensuring your CDK applications follow AWS security best practices.

    Basic implementation:
    ```typescript
    import { App } from 'aws-cdk-lib';
    import { AwsSolutionsChecks } from 'cdk-nag';

    const app = new App();
    // Create your stack
    const stack = new MyStack(app, 'MyStack');
    // Apply CDK Nag
    AwsSolutionsChecks.check(app);
    ```

    Optional integration patterns:

    1. Using environment variables:
    ```typescript
    if (process.env.ENABLE_CDK_NAG === 'true') {
      AwsSolutionsChecks.check(app);
    }
    ```

    2. Using CDK context parameters:
    ```typescript
    3. Environment-specific application:
    ```typescript
    const environment = app.node.tryGetContext('environment') || 'development';
    if (['production', 'staging'].includes(environment)) {
      AwsSolutionsChecks.check(stack);
    }
    ```

    For more information on specific rule packs:
    - Use resource `cdk-nag://rules/{rule_pack}` to get all rules for a specific pack
    - Use resource `cdk-nag://warnings/{rule_pack}` to get warnings for a specific pack
    - Use resource `cdk-nag://errors/{rule_pack}` to get errors for a specific pack

    Args:
        ctx: MCP context
        rule_id: The CDK Nag rule ID (e.g., 'AwsSolutions-IAM4')

    Returns:
        Dictionary with detailed explanation and remediation steps
    """
    # Use the resource we created to fetch the rule information
    try:
        rule_content = await get_rule(rule_id)

        # If the rule was found, return a structured response
        if not rule_content.startswith('Rule'):
            return {
                'rule_id': rule_id,
                'content': rule_content,
                'source': 'https://github.com/cdklabs/cdk-nag/blob/main/RULES.md',
                'status': 'success',
            }
        else:
            # Rule not found
            return {
                'rule_id': rule_id,
                'error': f'Rule {rule_id} not found in CDK Nag documentation.',
                'source': 'https://github.com/cdklabs/cdk-nag/blob/main/RULES.md',
                'status': 'not_found',
            }
    except Exception as e:
        # Handle any errors
        return {
            'rule_id': rule_id,
            'error': f'Failed to fetch rule information: {str(e)}',
            'source': 'https://github.com/cdklabs/cdk-nag/blob/main/RULES.md',
            'status': 'error',
        }


async def check_cdk_nag_suppressions_tool(
    ctx: Context,
    code: Optional[str] = None,
    file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Check if CDK code contains Nag suppressions that require human review.

    Scans TypeScript/JavaScript code for NagSuppressions usage to ensure security
    suppressions receive proper human oversight and justification.

    Args:
        ctx: MCP context
        code: CDK code to analyze (TypeScript/JavaScript)
        file_path: Path to a file containing CDK code to analyze

    Returns:
        Analysis results with suppression details and security guidance
    """
    # Use the imported function from cdk_nag_parser.py
    return check_cdk_nag_suppressions(code=code, file_path=file_path)


def save_fallback_script_to_file(
    script_content: str, lambda_code_path: str, output_path: str
) -> str:
    """Save fallback script to a file instead of including it in the response.

    Args:
        script_content: The script content to save
        lambda_code_path: Original Lambda file path (used for naming)
        output_path: Schema output path (used for directory)

    Returns:
        Path to the saved script file
    """
    # Sanitize paths to prevent path traversal attacks
    output_dir = os.path.dirname(os.path.abspath(output_path))
    
    # Create scripts directory in the same directory as the output file
    scripts_dir = os.path.join(output_dir, 'scripts')
    
    try:
        os.makedirs(scripts_dir, exist_ok=True)
    except (OSError, IOError) as e:
        logger.error(f"Failed to create scripts directory: {e}")
        # Fall back to output directory if scripts dir creation fails
        scripts_dir = output_dir
    
    # Sanitize file name - remove any path components and ensure it's just a base name
    lambda_file_name = os.path.basename(lambda_code_path)
    # Remove extension and any potentially problematic characters
    sanitized_name = os.path.splitext(lambda_file_name)[0]
    sanitized_name = re.sub(r'[^a-zA-Z0-9_-]', '', sanitized_name)
    
    # Generate script name
    script_file_name = f'generate_schema_{sanitized_name}.py'
    script_path = os.path.join(scripts_dir, script_file_name)
    
    # Validate the resulting path is still within the expected directory
    if not os.path.abspath(script_path).startswith(os.path.abspath(scripts_dir)):
        logger.error(f"Path traversal attempt detected: {script_path}")
        # Fall back to a safe default
        script_path = os.path.join(scripts_dir, 'generate_schema.py')
    
    try:
        # Write the script to file with restricted permissions
        # Open with restricted permissions from the start (only owner can read/write)
        with open(os.open(script_path, os.O_CREAT | os.O_WRONLY, 0o600), 'w') as f:
            f.write(script_content)
        
        # Update to executable permissions (only for the owner)
        os.chmod(script_path, 0o700)  # rwx------ permissions (owner only)
        
        logger.info(f"Successfully created script at {script_path}")
        return script_path
    
    except (OSError, IOError) as e:
        logger.error(f"Failed to save script: {e}")
        return f"Error saving script: {str(e)}"


async def bedrock_schema_generator_from_file(
    ctx: Context, lambda_code_path: str, output_path: str
) -> Dict[str, Any]:
    """Generate OpenAPI schema for Bedrock Agent Action Groups from a file.

    This tool converts a Lambda file with BedrockAgentResolver into a Bedrock-compatible
    OpenAPI schema. It uses a progressive approach to handle common issues:
    1. Direct import of the Lambda file
    2. Simplified version with problematic imports commented out
    3. Fallback script generation if needed

    Args:
        ctx: MCP context
        lambda_code_path: Path to Python file containing BedrockAgentResolver app
        output_path: Where to save the generated schema

    Returns:
        Dictionary with schema generation results, including status, path to generated schema,
        and diagnostic information if errors occurred
    """
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Generate the schema
    result = generate_bedrock_schema_from_file(
        lambda_code_path=lambda_code_path,
        output_path=output_path,
    )

    # If fallback script was generated, save it to a file instead of returning it in the response
    if result.get('status') == 'error' and result.get('fallback_script'):
        # Save the script to a file
        script_path = save_fallback_script_to_file(
            result['fallback_script'], lambda_code_path, output_path
        )

        # Get the output filename for use in examples
        output_filename = os.path.basename(output_path)
        output_dir = os.path.dirname(output_path)

        # Update the result dictionary to include the script path instead of script content
        result['fallback_script_path'] = script_path

        # Remove the full script content to avoid verbose responses
        del result['fallback_script']

        # Enhanced client instructions with CDK integration example
        result['client_instructions'] = {
            'title': 'Schema Generation and Integration Guide',
            'steps': [
                f"1. Run the script at '{script_path}'",
                f"2. The script will generate the schema file at '{output_path}'",
                '3. In your CDK code, reference this exact schema file as shown below:',
            ],
            'command_suggestion': f'python {script_path}',
            'cdk_integration_example': f"// Assuming your Lambda function is named '{os.path.basename(lambda_code_path).replace('.py', 'Lambda')}'\n"
            f'const {os.path.basename(lambda_code_path).replace(".py", "ActionGroup")} = new bedrock.AgentActionGroup({{\n'
            f'  name: "{os.path.basename(lambda_code_path).replace(".py", "ActionGroup")}",\n'
            f'  description: "This action group is used for {os.path.basename(lambda_code_path).replace(".py", "")}",\n'
            f'  executor: bedrock.ActionGroupExecutor.fromlambdaFunction({os.path.basename(lambda_code_path).replace(".py", "Lambda")}),\n'
            f'  apiSchema: bedrock.ApiSchema.fromLocalAsset(\n'
            f'    path.join(__dirname, "{os.path.relpath(output_dir, os.path.dirname(lambda_code_path))}", "{output_filename}")\n'
            f'  )\n'
            f'}});\n'
            f'agent.addActionGroup({os.path.basename(lambda_code_path).replace(".py", "ActionGroup")});',
            'important_notes': [
                '✅ Use the exact openapi.json file generated by the script',
                '✅ Adjust the path in fromLocalAsset() to point to where the schema was generated',
                '❌ Do NOT regenerate or modify the schema manually',
            ],
        }

        if 'instructions' in result:
            result['instructions'] = result['instructions'].replace(
                'save the fallback script to a file',
                f'run the fallback script located at {script_path}',
            )

        # Update the solution message
        result['solution'] = f'Use the fallback script at {script_path} to generate the schema'

    return result


async def get_aws_solutions_construct_pattern(
    ctx: Context,
    pattern_name: Optional[str] = None,
    services: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Search and discover AWS Solutions Constructs patterns.

    AWS Solutions Constructs are vetted architecture patterns that combine multiple
    AWS services to solve common use cases following AWS Well-Architected best practices.

    Key benefits:
    - Accelerated Development: Implement common patterns without boilerplate code
    - Best Practices Built-in: Security, reliability, and performance best practices
    - Reduced Complexity: Simplified interfaces for multi-service architectures
    - Well-Architected: Patterns follow AWS Well-Architected Framework principles

    When to use Solutions Constructs:
    - Implementing common architecture patterns (e.g., API + Lambda + DynamoDB)
    - You want secure defaults and best practices applied automatically
    - You need to quickly prototype or build production-ready infrastructure

    This tool provides metadata about patterns. For complete documentation,
    use the resource URI returned in the 'documentation_uri' field.

    Args:
        ctx: MCP context
        pattern_name: Optional name of the specific pattern (e.g., 'aws-lambda-dynamodb')
        services: Optional list of AWS services to search for patterns that use them
                 (e.g., ['lambda', 'dynamodb'])

    Returns:
        Dictionary with pattern metadata including description, services, and documentation URI
    """
    if pattern_name:
        result = await get_pattern_info(pattern_name)
        return result
    elif services:
        patterns = await search_patterns(services)
        return {
            'results': patterns,
            'count': len(patterns),
            'status': 'success',
            'metadata': {'services_searched': services},
        }
    else:
        available_patterns = await fetch_pattern_list()
        return {
            'error': 'Either pattern_name or services must be provided',
            'available_patterns': available_patterns,
            'status': 'error',
        }


async def search_genai_cdk_constructs(
    ctx: Context,
    query: Optional[str] = None,
    construct_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Search for GenAI CDK constructs by name or type.

    The search is flexible and will match any of your search terms (OR logic).
    It handles common variations like singular/plural forms and terms with/without spaces.

    Examples:
    - "bedrock agent" - Returns all agent-related constructs
    - "knowledgebase vector" - Returns knowledge base constructs related to vector stores
    - "agent actiongroups" - Returns action groups for agents

    Args:
        ctx: MCP context
        query: Search term(s) to find constructs by name or description
        construct_type: Optional filter by construct type ('bedrock', 'opensearchserverless', etc.)

    Returns:
        Dictionary with matching constructs and resource URIs
    """
    try:
        # Get list of constructs
        constructs = list_available_constructs(construct_type)

        # If no query, return all constructs
        if not query:
            results = []
            for construct in constructs:
                results.append(
                    {
                        'name': construct['name'],
                        'type': construct['type'],
                        'description': construct['description'],
                        'resource_uri': f'genai-cdk-constructs://{construct["type"]}/{construct["name"]}',
                    }
                )

            return {
                'results': results,
                'count': len(results),
                'status': 'success',
                'installation_required': {
                    'package_name': '@cdklabs/generative-ai-cdk-constructs',
                    'message': 'This construct requires the @cdklabs/generative-ai-cdk-constructs package to be installed',
                },
            }

        # Define functions to extract searchable text and name parts
        def get_text_fn(construct: Dict[str, Any]) -> str:
            # Create a searchable string from the construct
            name = construct['name'].lower().replace('_', ' ')
            # Split camelCase words (e.g., actionGroups -> action Groups)
            name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name).lower()
            return f'{name} {construct["type"]} {construct["description"]}'.lower()

        def get_name_parts_fn(construct: Dict[str, Any]) -> List[str]:
            name = construct['name'].lower().replace('_', ' ')
            # Split camelCase words
            name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name).lower()
            return name.split()

        # Use common search utility
        search_terms = query.lower().split()
        scored_constructs = search_utils.search_items_with_terms(
            constructs, search_terms, get_text_fn, get_name_parts_fn
        )

        # Format results with resource URIs and matched keywords
        results = []
        for scored_item in scored_constructs:
            construct = scored_item['item']
            results.append(
                {
                    'name': construct['name'],
                    'type': construct['type'],
                    'description': construct['description'],
                    'resource_uri': f'genai-cdk-constructs://{construct["type"]}/{construct["name"]}',
                    'matched_keywords': scored_item['matched_terms'],
                }
            )

        return {
            'results': results,
            'count': len(results),
            'status': 'success',
            'installation_required': {
                'package_name': '@cdklabs/generative-ai-cdk-constructs',
                'message': 'This construct requires the @cdklabs/generative-ai-cdk-constructs package to be installed',
            },
        }
    except Exception as e:
        return {'error': f'Error searching constructs: {str(e)}', 'status': 'error'}
