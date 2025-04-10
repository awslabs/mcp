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

"""awslabs MCP Cost Analysis mcp server implementation.

This server provides tools for analyzing AWS service costs across different user tiers.
"""

import argparse
import boto3
import logging
import os
from awslabs.cost_analysis_mcp_server.cdk_analyzer import analyze_cdk_project
from awslabs.cost_analysis_mcp_server.static.patterns import BEDROCK
from bs4 import BeautifulSoup
from httpx import AsyncClient
from mcp.server.fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    name='awslabs.cost-analysis-mcp-server',
    instructions="""Use this server for analyzing AWS service costs, with a focus on serverless services.

    REQUIRED WORKFLOW:
    Analyze costs of AWS services by following these steps in order:

    1. Primary Data Source:
       - MUST first invoke get_pricing_from_web() to scrape pricing from AWS pricing page

    2. Fallback Mechanism 1:
       - If web scraping fails, MUST use get_pricing_from_api() to fetch data via AWS Pricing API

    3. For Bedrock Services:
       - When analyzing Amazon Bedrock services, MUST also use get_bedrock_patterns()
       - This provides critical architecture patterns, component relationships, and cost considerations
       - Especially important for Knowledge Base, Agent, Guardrails, and Data Automation services

    4. Report Generation:
       - MUST generate cost analysis report using retrieved data via generate_cost_report()
       - The report includes sections for:
         * Service Overview
         * Architecture Pattern (for Bedrock services)
         * Assumptions
         * Limitations and Exclusions
         * Cost Breakdown
         * Cost Scaling with Usage
         * AWS Well-Architected Cost Optimization Recommendations

    5. Output:
       Return to user:
       - Detailed cost analysis report in markdown format
       - Source of the data (web scraping, API, or websearch)
       - List of attempted data retrieval methods

    ACCURACY GUIDELINES:
    - When uncertain about service compatibility or pricing details, EXCLUDE them rather than making assumptions
    - For database compatibility, only include CONFIRMED supported databases
    - For model comparisons, always use the LATEST models rather than specific named ones
    - Add clear disclaimers about what is NOT included in calculations
    - PROVIDING LESS INFORMATION IS BETTER THAN GIVING WRONG INFORMATION
    - For Bedrock Knowledge Base, ALWAYS account for OpenSearch Serverless minimum OCU requirements (2 OCUs, $345.60/month minimum)
    - For Bedrock Agent, DO NOT double-count foundation model costs (they're included in agent usage)

    IMPORTANT: Steps MUST be executed in this exact order. Each step must be attempted
    before moving to the next fallback mechanism. The report is particularly focused on
    serverless services and pay-as-you-go pricing models.""",
    dependencies=['pydantic', 'boto3', 'beautifulsoup4', 'websearch'],
)

profile_name = os.getenv('AWS_PROFILE', 'default')
logger.info(f'Using AWS profile {profile_name}')


@mcp.tool(
    name='analyze_cdk_project',
    description='Analyze a CDK project to identify AWS services used. This tool dynamically extracts service information from CDK constructs without relying on hardcoded service mappings.',
)
async def analyze_cdk_project_wrapper(project_path: str, ctx: Context) -> Optional[Dict]:
    """Analyze a CDK project to identify AWS services.

    Args:
        project_path: The path to the CDK project
        ctx: MCP context for logging and state management

    Returns:
        Dictionary containing the identified services and their configurations
    """
    try:
        analysis_result = await analyze_cdk_project(project_path)
        logger.info(f'Analysis result: {analysis_result}')
        if analysis_result and 'services' in analysis_result:
            return analysis_result
        else:
            logger.error(f'Invalid analysis result format: {analysis_result}')
            return {
                'status': 'error',
                'services': [],
                'message': f'Failed to analyze CDK project at {project_path}: Invalid result format',
                'details': {'error': 'Invalid result format'},
            }
    except Exception as e:
        await ctx.error(f'Failed to analyze CDK project: {e}')
        return None


@mcp.tool(
    name='get_pricing_from_web',
    description='Get pricing information from AWS pricing webpage. Service codes typically use lowercase with hyphens format (e.g., "opensearch-service" for both OpenSearch and OpenSearch Serverless, "api-gateway", "lambda"). Note that some services like OpenSearch Serverless are part of broader service codes (use "opensearch-service" not "opensearch-serverless"). Important: Web service codes differ from API service codes (e.g., use "opensearch-service" for web but "AmazonES" for API). When retrieving foundation model pricing, always use the latest models for comparison rather than specific named ones that may become outdated.',
)
async def get_pricing_from_web(service_code: str, ctx: Context) -> Optional[Dict]:
    """Get pricing information from AWS pricing webpage.

    Args:
        service_code: The service code (e.g., 'opensearch-service' for both OpenSearch and OpenSearch Serverless)
        ctx: MCP context for logging and state management

    Returns:
        Dict: Dictionary containing the pricing information retrieved from the AWS pricing webpage
    """
    try:
        for prefix in ['Amazon', 'AWS']:
            if service_code.startswith(prefix):
                service_code = service_code[len(prefix) :].lower()
        service_code = service_code.lower().strip()
        url = f'https://aws.amazon.com/{service_code}/pricing'
        async with AsyncClient() as client:
            response = await client.get(url, follow_redirects=True, timeout=10.0)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for script in soup(['script', 'style']):
                script.decompose()

            # Extract text content
            text = soup.get_text()

            # Break into lines and remove leading and trailing space on each
            lines = (line.strip() for line in text.splitlines())

            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split('  '))

            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)

            result = {
                'status': 'success',
                'service_name': service_code,
                'data': text,
                'message': f'Retrieved pricing for {service_code} from AWS Pricing url',
            }

            # No need to store in context, just return the result

            return result

    except Exception as e:
        await ctx.error(f'Failed to get pricing from web: {e}')
        return None


@mcp.tool(
    name='get_pricing_from_api',
    description="""Get pricing information from AWS Price List API.
    Service codes for API often differ from web URLs.
    (e.g., use "AmazonES" for OpenSearch, not "AmazonOpenSearchService").
    IMPORTANT GUIDELINES:
    - When retrieving foundation model pricing, always use the latest models for comparison
    - For database compatibility with services, only include confirmed supported databases
    - Providing less information is better than giving incorrect information""",
)
async def get_pricing_from_api(service_code: str, region: str, ctx: Context) -> Optional[Dict]:
    """Get pricing information from AWS Price List API. If the API request fails in the initial attempt, retry by modifying the service_code.

    Args:
        service_code: The service code (e.g., 'AmazonES' for OpenSearch, 'AmazonS3' for S3)
        region: AWS region (e.g., 'us-west-2')
        ctx: MCP context for logging and state management

    Returns:
        Dictionary containing pricing information from AWS Pricing API
    """
    try:
        pricing_client = boto3.Session(profile_name=profile_name).client(
            'pricing', region_name='us-east-1'
        )

        response = pricing_client.get_products(
            ServiceCode=service_code,
            Filters=[{'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': region}],
            MaxResults=100,
        )

        if not response['PriceList']:
            await ctx.error(f'Pricing API returned empty results for service code: {service_code}')
            return {
                'status': 'error',
                'error_type': 'empty_results',
                'message': f'The service code "{service_code}" did not return any pricing data. AWS service codes typically follow patterns like "AmazonS3", "AmazonEC2", "AmazonES", etc. Please check the exact service code and try again.',
                'examples': {
                    'OpenSearch': 'AmazonES',
                    'Lambda': 'AWSLambda',
                    'DynamoDB': 'AmazonDynamoDB',
                    'Bedrock': 'AmazonBedrock',
                },
            }

        result = {
            'status': 'success',
            'service_name': service_code,
            'data': response['PriceList'],
            'message': f'Retrieved pricing for {service_code} in {region} from AWS Pricing API',
        }

        # No need to store in context, just return the result

        return result

    except Exception as e:
        error_msg = str(e)
        await ctx.error(f'Pricing API request failed: {e}')

        # Just pass through the original error message
        return {
            'status': 'error',
            'error_type': 'api_error',
            'message': error_msg,
            'service_code': service_code,
            'region': region,
            'note': 'AWS service codes typically follow patterns like "AmazonS3", "AmazonEC2", "AmazonES" (for OpenSearch), etc.',
        }


@mcp.tool(
    name='get_bedrock_patterns',
    description='Get architecture patterns for Amazon Bedrock applications, including component relationships and cost considerations',
)
async def get_bedrock_patterns(ctx: Optional[Context] = None) -> str:
    """Get architecture patterns for Amazon Bedrock applications.

    This tool provides architecture patterns, component relationships, and cost considerations
    for Amazon Bedrock applications. It does not include specific pricing information, which
    should be obtained using get_pricing_from_web or get_pricing_from_api.

    Returns:
        String containing the architecture patterns in markdown format
    """
    return BEDROCK


# Default recommendation prompt template
DEFAULT_RECOMMENDATION_PROMPT = """
Based on the following AWS services and their relationships:
- Services: {services}
- Architecture patterns: {architecture_patterns}
- Pricing model: {pricing_model}

Generate cost optimization recommendations organized into two categories:

1. Immediate Actions: Specific, actionable recommendations that can be implemented quickly to optimize costs.

2. Best Practices: Longer-term strategies aligned with the AWS Well-Architected Framework's cost optimization pillar.

For each recommendation:
- Be specific to the services being used
- Consider service interactions and dependencies
- Include concrete cost impact where possible
- Avoid generic advice unless broadly applicable

Focus on the most impactful recommendations first. Do not limit yourself to a specific number of recommendations - include as many as are relevant and valuable.
"""


@mcp.tool(
    name='generate_cost_report',
    description="""Generate a detailed cost analysis report based on pricing data for one or more AWS services.

This tool requires AWS pricing data and provides options for adding detailed cost information.

IMPORTANT REQUIREMENTS:
- ALWAYS include detailed unit pricing information (e.g., "$0.0008 per 1K input tokens")
- ALWAYS show calculation breakdowns (unit price × usage = total cost)
- ALWAYS specify the pricing model (e.g., "ON DEMAND")
- ALWAYS list all assumptions and exclusions explicitly

Output Format Options:
- 'markdown' (default): Generates a well-formatted markdown report
- 'csv': Generates a CSV format report with sections for service information, unit pricing, cost calculations, etc.

Example usage:

```json
{
  // Required parameters
  "pricing_data": {
    // This should contain pricing data retrieved from get_pricing_from_web or get_pricing_from_api
    "status": "success",
    "service_name": "bedrock",
    "data": "... pricing information ...",
    "message": "Retrieved pricing for bedrock from AWS Pricing url"
  },
  "service_name": "Amazon Bedrock",

  // Core parameters (commonly used)
  "related_services": ["Lambda", "S3"],
  "pricing_model": "ON DEMAND",
  "assumptions": [
    "Standard ON DEMAND pricing model",
    "No caching or optimization applied",
    "Average request size of 4KB"
  ],
  "exclusions": [
    "Data transfer costs between regions",
    "Custom model training costs",
    "Development and maintenance costs"
  ],
  "output_file": "cost_analysis_report.md",  // or "cost_analysis_report.csv" for CSV format
  "format": "markdown",  // or "csv" for CSV format

  // Advanced parameter for complex scenarios
  "detailed_cost_data": {
    "services": {
      "Amazon Bedrock Foundation Models": {
        "usage": "Processing 1M input tokens and 500K output tokens with Claude 3.5 Haiku",
        "estimated_cost": "$80.00",
        "free_tier_info": "No free tier for Bedrock foundation models",
        "unit_pricing": {
          "input_tokens": "$0.0008 per 1K tokens",
          "output_tokens": "$0.0016 per 1K tokens"
        },
        "usage_quantities": {
          "input_tokens": "1,000,000 tokens",
          "output_tokens": "500,000 tokens"
        },
        "calculation_details": "$0.0008/1K × 1,000K input tokens + $0.0016/1K × 500K output tokens = $80.00"
      },
      "AWS Lambda": {
        "usage": "6,000 requests per month with 512 MB memory",
        "estimated_cost": "$0.38",
        "free_tier_info": "First 12 months: 1M requests/month free",
        "unit_pricing": {
          "requests": "$0.20 per 1M requests",
          "compute": "$0.0000166667 per GB-second"
        },
        "usage_quantities": {
          "requests": "6,000 requests",
          "compute": "6,000 requests × 1s × 0.5GB = 3,000 GB-seconds"
        },
        "calculation_details": "$0.20/1M × 0.006M requests + $0.0000166667 × 3,000 GB-seconds = $0.38"
      }
    }
  },

  // Recommendations parameter - can be provided directly or generated
  "recommendations": {
    "immediate": [
      "Optimize prompt engineering to reduce token usage for Claude 3.5 Haiku",
      "Configure Knowledge Base OCUs based on actual query patterns",
      "Implement response caching for common queries to reduce token usage"
    ],
    "best_practices": [
      "Monitor OCU utilization metrics and adjust capacity as needed",
      "Use prompt caching for repeated context across API calls",
      "Consider provisioned throughput for predictable workloads"
    ]
  }
}
```
""",
)
async def generate_cost_report_wrapper(
    pricing_data: Dict[str, Any],  # Required: Raw pricing data from AWS
    service_name: str,  # Required: Primary service name
    # Core parameters (simple, commonly used)
    related_services: Optional[List[str]] = None,
    pricing_model: str = 'ON DEMAND',
    assumptions: Optional[List[str]] = None,
    exclusions: Optional[List[str]] = None,
    output_file: Optional[str] = None,
    format: str = 'markdown',  # Output format ('markdown' or 'csv')
    # Advanced parameters (grouped in a dictionary for complex use cases)
    detailed_cost_data: Optional[Dict[str, Any]] = None,
    recommendations: Optional[
        Dict[str, Any]
    ] = None,  # Direct recommendations or guidance for generation
    ctx: Optional[Context] = None,
) -> str:
    """Generate a cost analysis report for AWS services.

    IMPORTANT: When uncertain about compatibility or pricing details, exclude them rather than making assumptions.
    For example:
    - For database compatibility with services like Structured Data Retrieval KB, only include confirmed supported databases
    - For model comparisons, always use the latest models rather than specific named ones that may become outdated
    - Add clear disclaimers about what is NOT included in calculations
    - Providing less information is better than giving WRONG information

    CRITICAL REQUIREMENTS:
    - ALWAYS include detailed unit pricing information (e.g., "$0.0008 per 1K input tokens")
    - ALWAYS show calculation breakdowns (unit price × usage = total cost)
    - ALWAYS specify the pricing model (e.g., "ON DEMAND")
    - ALWAYS list all assumptions and exclusions explicitly

    For Amazon Bedrock services, especially Knowledge Base, Agent, Guardrails, and Data Automation:
    - Use get_bedrock_patterns() to understand component relationships and cost considerations
    - For Knowledge Base, account for OpenSearch Serverless minimum OCU requirements (2 OCUs, $345.60/month minimum)
    - For Agent, avoid double-counting foundation model costs (they're included in agent usage)

    Args:
        pricing_data: Raw pricing data from AWS pricing tools (required)
        service_name: Name of the primary service (required)
        related_services: List of related services to include in the analysis
        pricing_model: The pricing model used (default: "ON DEMAND")
        assumptions: List of assumptions made for the cost analysis
        exclusions: List of items excluded from the cost analysis
        output_file: Path to save the report to a file
        format: Output format for the cost analysis report
            - Values: "markdown" (default) or "csv"
            - markdown: Generates a well-formatted report with tables and sections
            - csv: Generates a structured data format for spreadsheet compatibility
        detailed_cost_data: Dictionary containing detailed cost information for complex scenarios
            This can include:
            - services: Dictionary mapping service names to their detailed cost information
                - unit_pricing: Dictionary mapping price types to their values
                - usage_quantities: Dictionary mapping usage types to their quantities
                - calculation_details: String showing the calculation breakdown
        recommendations: Optional dictionary containing recommendations or guidance for generation
        ctx: MCP context for logging and error handling

    Returns:
        str: The generated document in markdown format
    """
    # Import and call the implementation from report_generator.py
    from awslabs.cost_analysis_mcp_server.report_generator import (
        generate_cost_report,
    )

    # 1. Extract services from pricing data and parameters
    services = service_name
    if related_services:
        services = f'{service_name}, {", ".join(related_services)}'

    # 2. Get architecture patterns if relevant (e.g., for Bedrock)
    architecture_patterns = {}
    if 'bedrock' in services.lower():
        try:
            # Get Bedrock architecture patterns
            bedrock_patterns = await get_bedrock_patterns(ctx)
            architecture_patterns['bedrock'] = bedrock_patterns
        except Exception as e:
            if ctx:
                await ctx.warning(f'Could not get Bedrock patterns: {e}')

    # 3. Process recommendations
    try:
        # Initialize detailed_cost_data if it doesn't exist
        if not detailed_cost_data:
            detailed_cost_data = {}

        # If recommendations are provided directly, use them
        if recommendations:
            detailed_cost_data['recommendations'] = recommendations
        # Otherwise, if no recommendations exist in detailed_cost_data, create a structure for the assistant to fill
        elif 'recommendations' not in detailed_cost_data:
            # Create a default prompt based on the services and context
            architecture_patterns_str = 'Available' if architecture_patterns else 'Not provided'

            prompt = DEFAULT_RECOMMENDATION_PROMPT.format(
                services=services,
                architecture_patterns=architecture_patterns_str,
                pricing_model=pricing_model,
            )

            detailed_cost_data['recommendations'] = {
                '_prompt': prompt,  # Include the prompt for reference
                'immediate': [],  # assistant will fill these
                'best_practices': [],  # assistant will fill these
            }
    except Exception as e:
        if ctx:
            await ctx.warning(f'Could not prepare recommendations: {e}')

    # 6. Call the report generator with the enhanced data
    return await generate_cost_report(
        pricing_data=pricing_data,
        service_name=service_name,
        related_services=related_services,
        pricing_model=pricing_model,
        assumptions=assumptions,
        exclusions=exclusions,
        output_file=output_file,
        detailed_cost_data=detailed_cost_data,
        ctx=ctx,
        format=format,
    )


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(description='Analyze cost of AWS services')
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':
    main()
