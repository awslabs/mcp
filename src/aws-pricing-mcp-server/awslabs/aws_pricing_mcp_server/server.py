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

"""awslabs MCP AWS Pricing mcp server implementation.

This server provides tools for analyzing AWS service costs across different user tiers.
"""

import os
import sys
from awslabs.aws_pricing_mcp_server import consts
from awslabs.aws_pricing_mcp_server.cdk_analyzer import analyze_cdk_project
from awslabs.aws_pricing_mcp_server.models import ErrorResponse, PricingFilters
from awslabs.aws_pricing_mcp_server.pricing_client import create_pricing_client
from awslabs.aws_pricing_mcp_server.static.patterns import BEDROCK
from awslabs.aws_pricing_mcp_server.terraform_analyzer import analyze_terraform_project
from bs4 import BeautifulSoup
from httpx import AsyncClient
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from pydantic.fields import FieldInfo
from typing import Any, Dict, List, Optional


# Set up logging
logger.remove()
logger.add(sys.stderr, level=consts.LOG_LEVEL)


async def create_error_response(
    ctx: Context,
    error_type: str,
    message: str,
    **kwargs,  # Accept any additional fields dynamically
) -> Dict[str, Any]:
    """Create a standardized error response, log it, and notify context."""
    logger.error(message)
    await ctx.error(message)

    error_response = ErrorResponse(
        error_type=error_type,
        message=message,
        **kwargs,
    )

    return error_response.model_dump()


mcp = FastMCP(
    name='awslabs.aws-pricing-mcp-server',
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
    dependencies=['pydantic', 'loguru', 'boto3', 'beautifulsoup4', 'websearch'],
)

profile_name = os.getenv('AWS_PROFILE', 'default')
logger.info(f'Using AWS profile {profile_name}')


@mcp.tool(
    name='analyze_cdk_project',
    description='Analyze a CDK project to identify AWS services used. This tool dynamically extracts service information from CDK constructs without relying on hardcoded service mappings.',
)
async def analyze_cdk_project_wrapper(
    ctx: Context,
    project_path: str = Field(..., description='Path to the project directory'),
) -> Optional[Dict]:
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
    name='analyze_terraform_project',
    description='Analyze a Terraform project to identify AWS services used. This tool dynamically extracts service information from Terraform resource declarations.',
)
async def analyze_terraform_project_wrapper(
    ctx: Context,
    project_path: str = Field(..., description='Path to the project directory'),
) -> Optional[Dict]:
    """Analyze a Terraform project to identify AWS services.

    Args:
        project_path: The path to the Terraform project
        ctx: MCP context for logging and state management

    Returns:
        Dictionary containing the identified services and their configurations
    """
    try:
        analysis_result = await analyze_terraform_project(project_path)
        logger.info(f'Analysis result: {analysis_result}')
        if analysis_result and 'services' in analysis_result:
            return analysis_result
        else:
            logger.error(f'Invalid analysis result format: {analysis_result}')
            return {
                'status': 'error',
                'services': [],
                'message': f'Failed to analyze Terraform project at {project_path}: Invalid result format',
                'details': {'error': 'Invalid result format'},
            }
    except Exception as e:
        await ctx.error(f'Failed to analyze Terraform project: {e}')
        return None


@mcp.tool(
    name='get_pricing_from_web',
    description='Get pricing information from AWS pricing webpage. Service codes typically use lowercase with hyphens format (e.g., "opensearch-service" for both OpenSearch and OpenSearch Serverless, "api-gateway", "lambda"). Note that some services like OpenSearch Serverless are part of broader service codes (use "opensearch-service" not "opensearch-serverless"). Important: Web service codes differ from API service codes (e.g., use "opensearch-service" for web but "AmazonES" for API). When retrieving foundation model pricing, always use the latest models for comparison rather than specific named ones that may become outdated.',
)
async def get_pricing_from_web(
    ctx: Context,
    service_code: str = Field(
        ...,
        description='AWS service code for web pricing (lowercase with hyphens, e.g., "opensearch-service", "lambda")',
    ),
) -> Optional[Dict]:
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
    description="""
    Get detailed pricing information from AWS Price List API with optional filters.

    Service codes for API often differ from web URLs.
    (e.g., use "AmazonES" for OpenSearch, not "AmazonOpenSearchService").
    List of service codes can be found with `curl 'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/index.json' | jq -r '.offers| .[] | .offerCode'`
    IMPORTANT GUIDELINES:
    - When retrieving foundation model pricing, always use the latest models for comparison
    - For database compatibility with services, only include confirmed supported databases
    - Providing less information is better than giving incorrect information

    **TOOL PURPOSE:**
    Retrieve AWS pricing data for various analysis needs: cost optimization, regional comparisons, compliance reporting, budget planning, or general pricing research.

    **YOUR APPROACH:**
    Follow a systematic discovery workflow to ensure accurate, complete results regardless of your specific use case.

    **MANDATORY WORKFLOW - ALWAYS FOLLOW:**

    **Step 1: Build Precise Filters**
    ```python
    # FOR COST OPTIMIZATION: Create matrix of ALL minimum qualifying combinations
    filters = {
       "filters": [
           {"Field": "memory", "Value": "8 GiB", "Type": "TERM_MATCH"},
           {"Field": "instanceType", "Value": "m5.large", "Type": "TERM_MATCH"}
       ]
    }
    ```

    **Step 2: Execute Query**
    ```python
    pricing = get_pricing_from_api('AmazonEC2', 'us-east-1', filters)
    ```

    **COMMON USE CASES:**

    **Cost Optimization (CRITICAL):**
    - Build complete cross-product matrix of ALL qualifying attribute combinations
    - Test every combination systematically: example: (min_memory × qualifying_storage × other_attributes)
    - Start with minimum thresholds, test ALL possibilities - don't stop at first match
    - Compare prices to find most cost-effective solution
    - Prove optimality: Verify no cheaper option exists within requirements

    **Regional Comparison:**
    - Use identical filters across different regions
    - Compare same instance types between us-east-1 vs eu-west-1
    - Analyze pricing variations for capacity planning

    **Compliance/Reporting:**
    - Retrieve pricing for specific instance families or configurations
    - Generate cost reports for budget planning
    - Document pricing for procurement processes

    **Research/Analysis:**
    - Compare pricing across different service tiers
    - Analyze cost implications of different configurations
    - Investigate pricing patterns for forecasting

    **CRITICAL REQUIREMENTS:**
    - **USE SPECIFIC FILTERS**: Large services (EC2, RDS) require 2-3 filters minimum
    - **VERIFY EXISTENCE**: Ensure all filter values exist in the service before querying
    - **FOR "CHEAPEST" QUERIES**: Build complete matrix, test ALL qualifying combinations, prove optimality

    **CONTEXT AND CONSTRAINTS:**
    - **CURRENT PRICING ONLY:** Use get_price_list_file for historical data
    - **NO SAVINGS PLANS/SPOT:** Only On-Demand and Reserved Instance pricing
    - **REGION AUTO-FILTER:** 'region' parameter creates regionCode filter automatically

    **REQUIRED INPUTS:**
    - `service_code`: (e.g., 'AmazonEC2', 'AmazonS3')
    - `region`: AWS region (e.g., 'us-east-1')
    - `filters`: Built using discovered values (MANDATORY for large services)
    - `max_allowed_characters`: Response limit (default: 100,000)

    **ANTI-PATTERNS - AVOID THESE:**
    ❌ Using broad queries without specific filters on large services
    ❌ Assuming attribute values exist across different services/regions
    ❌ **Stopping at first qualifying option when seeking cheapest price**
    ❌ **Testing only "obvious" instance sizes - smaller may be cheaper**

    **EXAMPLE USE CASES:**

    **1. Cost Optimization Example:**
    ```python
    # Find cheapest option meeting requirements
    qualifying_memory = [m for m in memory_options if meets_requirement(m, "≥8GB")]
    # Test combinations starting with minimum qualifying specs
    ```

    **2. Regional Comparison Example:**
    ```python
    # Compare same configuration across regions
    filters = {"filters": [{"Field": "instanceType", "Value": "m5.large", "Type": "TERM_MATCH"}]}
    us_pricing = get_pricing_from_api('AmazonEC2', 'us-east-1', filters)
    eu_pricing = get_pricing_from_api('AmazonEC2', 'eu-west-1', filters)
    ```

    **3. Research/Analysis Example:**
    ```python
    # Compare different memory tiers for same instance family
    memory_tiers = ["4 GiB", "8 GiB", "16 GiB"]
    for memory in memory_tiers:
       filters = {"filters": [{"Field": "memory", "Value": memory, "Type": "TERM_MATCH"}]}
       pricing = get_pricing_from_api('AmazonEC2', 'us-east-1', filters)
    ```

    **FILTERING STRATEGY:**
    - **Large Services (EC2, RDS)**: ALWAYS use 2-3 specific filters to prevent 200+ record responses
    - **Small Services**: May work with single filter or no filters
    - **Multi-Region Analysis**: Use identical filters across regions for accurate comparison
    - **Requirement-Based**: Systematically discover ALL options meeting criteria
    - **Cost Optimization**: Start with minimum qualifying thresholds, use minimum-threshold filtering, test all qualifying combinations

    **SUCCESS CRITERIA:**
    ✅ Applied appropriate filters for the service size
    ✅ For cost optimization: tested all qualifying combinations and proved optimality
    """,
)
async def get_pricing_from_api(
    ctx: Context,
    service_code: str = Field(
        ..., description='AWS service code (e.g., "AmazonEC2", "AmazonS3", "AmazonES")'
    ),
    region: str = Field(
        ..., description='AWS region (e.g., "us-east-1", "us-west-2", "eu-west-1")'
    ),
    filters: Optional[PricingFilters] = Field(
        None, description='Optional filters for pricing queries'
    ),
) -> Dict[str, Any]:
    """Get pricing information from AWS Price List API.

    Args:
        service_code: The service code (e.g., 'AmazonES' for OpenSearch, 'AmazonS3' for S3)
        region: AWS region (e.g., 'us-west-2')
        filters: Optional list of filter dictionaries in format {'Field': str, 'Type': str, 'Value': str}
        ctx: MCP context for logging and state management

    Returns:
        Dictionary containing pricing information from AWS Pricing API
    """
    # Handle Pydantic Field objects when called directly (not through MCP framework)
    if isinstance(filters, FieldInfo):
        filters = filters.default

    logger.info(f'Getting pricing for {service_code} in {region}')

    # Create pricing client with error handling
    try:
        pricing_client = create_pricing_client()
    except Exception as e:
        return await create_error_response(
            ctx=ctx,
            error_type='client_creation_failed',
            message=f'Failed to create AWS Pricing client: {str(e)}',
            service_code=service_code,
            region=region,
        )

    # Build filters
    try:
        # Start with the region filter
        region_filter = {'Field': 'regionCode', 'Type': 'TERM_MATCH', 'Value': region}
        api_filters = [region_filter]

        # Add any additional filters if provided
        if filters and filters.filters:
            api_filters.extend([f.model_dump(by_alias=True) for f in filters.filters])

        # Make the API request
        response = pricing_client.get_products(
            ServiceCode=service_code,
            Filters=api_filters,
            MaxResults=100,
        )
    except Exception as e:
        return await create_error_response(
            ctx=ctx,
            error_type='api_error',
            message=f'Failed to retrieve pricing data for service "{service_code}" in region "{region}": {str(e)}',
            service_code=service_code,
            region=region,
            suggestion='Verify that the service code and region combination is valid.',
        )

    # Check if results are empty
    if not response.get('PriceList'):
        return await create_error_response(
            ctx=ctx,
            error_type='empty_results',
            message=f'The service "{service_code}" did not return any pricing data. AWS service codes typically follow patterns like "AmazonS3", "AmazonEC2", "AmazonES", etc. Please check the exact service code and try again.',
            service_code=service_code,
            region=region,
            examples={
                'OpenSearch': 'AmazonES',
                'Lambda': 'AWSLambda',
                'DynamoDB': 'AmazonDynamoDB',
                'Bedrock': 'AmazonBedrock',
            },
        )

    price_list = response['PriceList']
    total_count = len(price_list)

    # Success response
    logger.info(f'Successfully retrieved {total_count} pricing items for {service_code}')
    await ctx.info(f'Successfully retrieved pricing for {service_code} in {region}')

    return {
        'status': 'success',
        'service_name': service_code,
        'data': price_list,
        'message': f'Retrieved pricing for {service_code} in {region} from AWS Pricing API',
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
    ctx: Context,
    pricing_data: Dict[str, Any] = Field(
        ..., description='Raw pricing data from AWS pricing tools'
    ),
    service_name: str = Field(..., description='Name of the AWS service'),
    # Core parameters (simple, commonly used)
    related_services: Optional[List[str]] = Field(
        None, description='List of related AWS services'
    ),
    pricing_model: str = Field(
        'ON DEMAND', description='Pricing model (e.g., "ON DEMAND", "Reserved")'
    ),
    assumptions: Optional[List[str]] = Field(
        None, description='List of assumptions for cost analysis'
    ),
    exclusions: Optional[List[str]] = Field(
        None, description='List of items excluded from cost analysis'
    ),
    output_file: Optional[str] = Field(None, description='Path to save the report file'),
    format: str = Field('markdown', description='Output format ("markdown" or "csv")'),
    # Advanced parameters (grouped in a dictionary for complex use cases)
    detailed_cost_data: Optional[Dict[str, Any]] = Field(
        None, description='Detailed cost information for complex scenarios'
    ),
    recommendations: Optional[Dict[str, Any]] = Field(
        None, description='Direct recommendations or guidance for generation'
    ),
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
    from awslabs.aws_pricing_mcp_server.report_generator import (
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
    mcp.run()


if __name__ == '__main__':
    main()
