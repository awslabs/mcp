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

"""AWS CDK MCP tool implementations."""

import logging
import re
from model_context_protocol import Context, ToolCallResult

from awslabs.cdk_mcp_server.data.lambda_layer_parser import LambdaLayerParser
from awslabs.cdk_mcp_server.data.solutions_constructs_parser import get_pattern_info, search_patterns
from awslabs.cdk_mcp_server.data.schema_generator import generate_schema_from_file, format_generated_schema
from awslabs.cdk_mcp_server.data.genai_cdk_loader import (
    search_genai_cdk_constructs,
    get_genai_cdk_construct_types,
)
from typing import Any, Dict, List, Optional

# Set up logging
logger = logging.getLogger(__name__)


async def cdk_guidance(ctx: Context) -> Dict[str, Any]:
    """Use this tool to get prescriptive CDK advice for building applications on AWS.

    Args:
        ctx: MCP context
    """
    # Just import to get the content from the file
    from awslabs.cdk_mcp_server.static import CDK_GENERAL_GUIDANCE

    return {"guidance": CDK_GENERAL_GUIDANCE}


async def explain_cdk_nag_rule(ctx: Context, rule_id: str) -> Dict[str, Any]:
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
    from awslabs.cdk_mcp_server.static import CDK_NAG_GUIDANCE

    # Regex to extract rule name from rule_id
    match = re.search(r'([A-Za-z]+)-([A-Za-z0-9]+)(\d+)', rule_id)
    if not match:
        return {
            "error": f"Invalid rule ID format: {rule_id}. Expected format: '<RulePack>-<Category><Number>' (e.g., AwsSolutions-IAM4)"
        }

    rule_pack, category, number = match.groups()
    full_rule_name = f"{category}{number}"

    # Look for a section with the rule ID in the guidance document
    rule_pattern = re.compile(
        fr'#+\s+{re.escape(rule_id)}|#+\s+{re.escape(full_rule_name)}', re.IGNORECASE
    )
    rule_match = rule_pattern.search(CDK_NAG_GUIDANCE)

    if not rule_match:
        return {
            "error": f"Rule {rule_id} not found in guidance document.",
            "available_rules": "Use resource 'cdk-nag://rules/AWS Solutions' to see all available rules.",
        }

    # Extract the rule section
    start_pos = rule_match.start()
    next_rule_match = re.search(r'#+\s+[A-Za-z]+-[A-Za-z0-9]+\d+', CDK_NAG_GUIDANCE[start_pos + 1 :])
    end_pos = (
        start_pos + 1 + next_rule_match.start() if next_rule_match else len(CDK_NAG_GUIDANCE)
    )

    rule_guidance = CDK_NAG_GUIDANCE[start_pos:end_pos].strip()

    # Extract summary, risk, and remediation if available
    summary_match = re.search(r'#+\s*Summary\s*\n+(.*?)(?=#+|\Z)', rule_guidance, re.DOTALL)
    summary = summary_match.group(1).strip() if summary_match else ""

    risk_match = re.search(r'#+\s*Risk\s*\n+(.*?)(?=#+|\Z)', rule_guidance, re.DOTALL)
    risk = risk_match.group(1).strip() if risk_match else ""

    remediation_match = re.search(
        r'#+\s*Remediation\s*\n+(.*?)(?=#+|\Z)', rule_guidance, re.DOTALL
    )
    remediation = remediation_match.group(1).strip() if remediation_match else ""

    code_examples_match = re.search(
        r'#+\s*Code Examples\s*\n+(.*?)(?=#+|\Z)', rule_guidance, re.DOTALL
    )
    code_examples = code_examples_match.group(1).strip() if code_examples_match else ""

    result = {
        "rule_id": rule_id,
        "rule_pack": rule_pack,
        "full_guidance": rule_guidance,
    }

    if summary:
        result["summary"] = summary
    if risk:
        result["risk"] = risk
    if remediation:
        result["remediation"] = remediation
    if code_examples:
        result["code_examples"] = code_examples

    return result


async def check_cdk_nag_suppressions_tool(
    ctx: Context, code: Optional[str] = None, file_path: Optional[str] = None
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
    if not code and not file_path:
        return {
            "error": "Either code or file_path must be provided",
            "suppressions_found": 0,
            "details": [],
        }

    if file_path:
        try:
            with open(file_path, "r") as f:
                code = f.read()
        except Exception as e:
            return {
                "error": f"Failed to read file: {str(e)}",
                "suppressions_found": 0,
                "details": [],
            }

    if not code:
        return {
            "error": "No code provided",
            "suppressions_found": 0,
            "details": [],
        }

    # Look for NagSuppressions.addResourceSuppressions or NagSuppressions.addStackSuppressions
    suppression_pattern = re.compile(
        r'NagSuppressions\.add(?:Resource|Stack)Suppressions\s*\(\s*([^,]+)(?:,\s*\[([^\]]+)\])?(?:,\s*{([^}]+)})?\s*\)'
    )
    matches = suppression_pattern.finditer(code)

    suppressions = []
    for match in matches:
        resource = match.group(1).strip()
        rules = []
        if match.group(2):
            # Extract rules from the array
            rule_pattern = re.compile(r'[\'"]([^\'"]+)[\'"]')
            rules = rule_pattern.findall(match.group(2))

        reason = None
        if match.group(3):
            # Extract reason if it exists
            reason_match = re.search(r'reason\s*:\s*[\'"]([^\'"]+)[\'"]', match.group(3))
            if reason_match:
                reason = reason_match.group(1)

        suppressions.append(
            {
                "resource": resource,
                "rules": rules,
                "reason": reason,
                "has_reason": reason is not None,
            }
        )

    # High-risk rules that should always be justified
    high_risk_rules = [
        "AwsSolutions-IAM4",
        "AwsSolutions-IAM5",
        "AwsSolutions-L1",
        "AwsSolutions-S1",
        "AwsSolutions-S2",
        "AwsSolutions-S10",
    ]

    # Check for high-risk suppressions without reasons
    high_risk_suppressions = []
    for suppression in suppressions:
        if not suppression["has_reason"]:
            high_risk_rules_suppressed = [rule for rule in suppression["rules"] if rule in high_risk_rules]
            if high_risk_rules_suppressed:
                high_risk_suppressions.append(
                    {
                        "resource": suppression["resource"],
                        "rules": high_risk_rules_suppressed,
                        "recommendation": "Add a detailed reason for suppressing these high-risk rules",
                    }
                )

    # Generate summary
    suppressions_without_reason = sum(1 for s in suppressions if not s["has_reason"])

    return {
        "suppressions_found": len(suppressions),
        "suppressions_without_reason": suppressions_without_reason,
        "high_risk_suppressions": len(high_risk_suppressions),
        "details": suppressions,
        "high_risk_details": high_risk_suppressions,
        "recommendation": """
Best practices for CDK Nag suppressions:
1. Always include a reason for every suppression
2. Document why the rule is not applicable in your specific case
3. Include a JIRA ticket or other reference if this is a temporary suppression
4. Consider adding a @todo comment with a timeline for addressing the issue
5. For high-risk rules, perform additional security review before suppressing
""",
    }


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
    try:
        logger.info(f"Generating schema from {lambda_code_path}")

        # Try to generate schema from the file
        schema_result = await generate_schema_from_file(lambda_code_path)

        # If we have a schema, save it to the output path
        if schema_result.get("schema"):
            try:
                formatted_schema = format_generated_schema(schema_result["schema"])
                with open(output_path, "w") as f:
                    f.write(formatted_schema)
                logger.info(f"Schema generated successfully and saved to {output_path}")
                schema_result["output_path"] = output_path
            except Exception as e:
                schema_result["error"] = f"Failed to save schema to {output_path}: {str(e)}"
                logger.error(schema_result["error"])

        return schema_result
    except Exception as e:
        error_message = f"Failed to generate schema: {str(e)}"
        logger.error(error_message)
        return {"status": "error", "error": error_message}


async def get_aws_solutions_construct_pattern(
    ctx: Context, pattern_name: Optional[str] = None, services: Optional[List[str]] = None
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
    # If pattern_name is provided, get info for that specific pattern
    if pattern_name:
        pattern_info = await get_pattern_info(pattern_name)
        if 'error' in pattern_info:
            return pattern_info
        return pattern_info

    # If services is provided, search for patterns that use those services
    if services:
        patterns = await search_patterns(services)
        return {
            "status": "success",
            "patterns_found": len(patterns),
            "patterns": patterns,
            "services_searched": services,
        }

    # If neither is provided, return an error
    return {
        "error": "Either pattern_name or services must be provided",
        "examples": {
            "pattern_name": "aws-lambda-dynamodb",
            "services": ["lambda", "dynamodb"],
        },
    }


async def search_genai_cdk_constructs(
    ctx: Context, query: Optional[str] = None, construct_type: Optional[str] = None
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
    # If neither query nor construct_type is provided, return available construct types
    if not query and not construct_type:
        construct_types = get_genai_cdk_construct_types()
        return {
            "status": "no_search_terms",
            "message": "Please provide a search query or construct type",
            "available_construct_types": construct_types,
            "examples": {
                "query": "agent actiongroups",
                "construct_type": "bedrock",
            },
        }

    # Perform the search
    search_results = await search_genai_cdk_constructs(query, construct_type)

    return {
        "status": "success",
        "results": search_results,
        "query": query,
        "construct_type": construct_type,
    }


async def generate_lambda_layer_code(
    ctx: Context,
    layer_type: str,  # "generic" or "python"
    entry_path: str,
    layer_name: str,
    compatible_runtimes: Optional[List[str]] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate CDK code for Lambda layers.
    
    This tool creates CDK code snippets for Lambda layers using best practices
    from the AWS documentation.
    
    Args:
        ctx: MCP context
        layer_type: Type of layer ("generic" or "python")
        entry_path: Path to the layer code
        layer_name: Name for the layer construct
        compatible_runtimes: List of compatible Lambda runtimes
        description: Optional description for the layer
        
    Returns:
        Dictionary with generated code snippets and documentation from AWS docs
    """
    # Fetch Lambda layer documentation
    docs = await LambdaLayerParser.fetch_lambda_layer_docs()
    
    # Format compatible runtimes
    if compatible_runtimes:
        runtime_strings = [f"lambda.Runtime.{runtime.upper()}" for runtime in compatible_runtimes]
        formatted_runtimes = ", ".join(runtime_strings)
    else:
        # Use latest versions
        if layer_type.lower() == "python":
            formatted_runtimes = "lambda.Runtime.PYTHON_3_13"
        else:
            formatted_runtimes = "lambda.Runtime.NODEJS_22_X"
    
    # Generate code based on layer type
    if layer_type.lower() == "python":
        code = f"""
import * as path from 'path';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import {{ PythonLayerVersion }} from '@aws-cdk/aws-lambda-python-alpha';

// Create a Python Lambda layer
const {layer_name} = new PythonLayerVersion(this, '{layer_name}', {{
  entry: path.join(__dirname, '{entry_path}'),  // Directory containing requirements.txt
  compatibleRuntimes: [{formatted_runtimes}],
  description: '{description or ""}',
}});
"""
    else:  # generic
        code = f"""
import * as path from 'path';
import * as lambda from 'aws-cdk-lib/aws-lambda';

// Create a generic Lambda layer
const {layer_name} = new lambda.LayerVersion(this, '{layer_name}', {{
  code: lambda.Code.fromAsset(path.join(__dirname, '{entry_path}')),
  compatibleRuntimes: [{formatted_runtimes}],
  description: '{description or ""}',
}});
"""

    # Return the result with documentation directly from AWS
    layer_docs = docs[f"{layer_type.lower()}_layers"]
    return {
        "code": code,
        "documentation": layer_docs,
        "best_practices": """
## Lambda Layer Best Practices

1. **Minimize Layer Size**: Keep layers focused on a single responsibility and minimize dependencies
2. **Version Pinning**: Pin dependency versions in requirements.txt to ensure consistent builds
3. **Layer Organization**: Follow the expected directory structure for your runtime
4. **Caching**: Use asset hashing to take advantage of CDK's built-in layer caching
5. **Testing**: Test your layers thoroughly with the runtimes they support
6. **Documentation**: Document what's in each layer and why it exists
"""
    }
