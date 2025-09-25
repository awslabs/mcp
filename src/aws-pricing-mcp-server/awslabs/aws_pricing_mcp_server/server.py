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

import sys
from awslabs.aws_pricing_mcp_server import consts
from awslabs.aws_pricing_mcp_server.cdk_analyzer import analyze_cdk_project
from awslabs.aws_pricing_mcp_server.models import (
    ATTRIBUTE_NAMES_FIELD,
    EFFECTIVE_DATE_FIELD,
    FILTERS_FIELD,
    GET_PRICING_MAX_ALLOWED_CHARACTERS_FIELD,
    MAX_RESULTS_FIELD,
    NEXT_TOKEN_FIELD,
    OUTPUT_OPTIONS_FIELD,
    REGION_FIELD,
    SERVICE_CODE_FIELD,
    ErrorResponse,
    OutputOptions,
    PricingFilter,
)
from awslabs.aws_pricing_mcp_server.pricing_client import (
    create_pricing_client,
    get_currency_for_region,
)
from awslabs.aws_pricing_mcp_server.pricing_transformer import transform_pricing_data
from awslabs.aws_pricing_mcp_server.static.patterns import BEDROCK
from awslabs.aws_pricing_mcp_server.terraform_analyzer import analyze_terraform_project
from datetime import datetime, timezone
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from pydantic.fields import FieldInfo
from typing import Any, Dict, List, Optional, Union


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
    instructions="""This server provides two primary functionalities:

    # USE CASE 1: AWS SERVICE CATALOG & PRICING DISCOVERY
    Access AWS service catalog information and pricing details through a structured workflow:

    1. Discovery Workflow:
       - get_pricing_service_codes: Retrieve all available AWS service codes (starting point)
       - get_pricing_service_attributes: Get filterable attributes for a specific service
       - get_pricing_attribute_values: Get possible values for a specific attribute
       - get_pricing: Get actual pricing data with optional filters
       - get_price_list_urls: Get bulk pricing data files in multiple formats (CSV, JSON) for historical pricing analysis

    2. Example Discovery Flow:
       ```
       # Get all service codes to find the one you need
       service_codes = get_pricing_service_codes()

       # Get available attributes for filtering EC2 pricing
       attributes = get_pricing_service_attributes('AmazonEC2')

       # Get all possible instance types for EC2
       instance_types = get_pricing_attribute_values('AmazonEC2', 'instanceType')

       # Get pricing for specific instance types in a region
       filters = [{"Field": "instanceType", "Value": "t3.medium", "Type": "TERM_MATCH"}]
       pricing = get_pricing('AmazonEC2', 'us-east-1', filters)

       # Get bulk pricing data files for historical analysis
       price_list = get_price_list_urls('AmazonEC2', 'us-east-1')
       # Returns: {'arn': '...', 'urls': {'csv': 'https://...', 'json': 'https://...'}}
       ```

    # USE CASE 2: COST ANALYSIS REPORT GENERATION
    Generate comprehensive cost reports for AWS services by following these steps:

    1. Data Gathering: Invoke get_pricing() to fetch data via AWS Pricing API

    2. Service-Specific Analysis:
       - For Bedrock Services: MUST also use get_bedrock_patterns()
       - This provides critical architecture patterns, component relationships, and cost considerations
       - Especially important for Knowledge Base, Agent, Guardrails, and Data Automation services

    3. Report Generation:
       - MUST generate cost analysis report using retrieved data via generate_cost_report()
       - The report includes sections for:
         * Service Overview
         * Architecture Pattern (for Bedrock services)
         * Assumptions
         * Limitations and Exclusions
         * Cost Breakdown
         * Cost Scaling with Usage
         * AWS Well-Architected Cost Optimization Recommendations

    4. Output:
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

    IMPORTANT: For report generation, steps MUST be executed in the exact order specified. Each step must be attempted
    before moving to the next fallback mechanism. The report is particularly focused on
    serverless services and pay-as-you-go pricing models.""",
    dependencies=['pydantic', 'loguru', 'boto3', 'beautifulsoup4', 'websearch'],
)


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
    name='get_pricing',
    description="""
    Get detailed pricing information from AWS Price List API with optional filters.

    **PARAMETERS:**
    - service_code (required): AWS service code (e.g., 'AmazonEC2', 'AmazonS3', 'AmazonES')
    - region (required): AWS region string (e.g., 'us-east-1') OR list for multi-region comparison (e.g., ['us-east-1', 'eu-west-1'])
    - filters (optional): List of filter dictionaries in format {'Field': str, 'Type': str, 'Value': str}
    - max_allowed_characters (optional): Response size limit in characters (default: 100,000, use -1 for unlimited)
    - output_options (optional): OutputOptions object for response transformation and size reduction
    - max_results (optional): Maximum number of results to return per page (default: 100, min: 1, max: 100)
    - next_token (optional): Pagination token from previous response to get next page of results

    **MANDATORY WORKFLOW - ALWAYS FOLLOW:**

    **Step 1: Discover Available Options**
    ```python
    service_codes = get_pricing_service_codes()                              # Find correct service (skip if known)
    attributes = get_pricing_service_attributes('AmazonEC2')                 # Discover filterable dimensions
    attribute_values = get_pricing_attribute_values('AmazonEC2', 'memory')   # Get valid values for filtering
    ```

    **Step 2: Build Precise Filters**
    ```python
    # Use ONLY values discovered in Step 1
    filters = [
       {"Field": "memory", "Value": ["8 GiB", "16 GiB", "32 GiB"], "Type": "ANY_OF"},     # Multiple options
       {"Field": "instanceType", "Value": "m5", "Type": "CONTAINS"},                      # Pattern matching
       {"Field": "instanceType", "Value": ["t2", "m4"], "Type": "NONE_OF"}                # Exclude older
   ]
    ```

    **Step 3: Execute Query**
    ```python
    pricing = get_pricing('AmazonEC2', 'us-east-1', filters)
    ```

    **FILTER TYPES:**
    - **EQUALS**: Exact match (default) - `{"Field": "instanceType", "Value": "m5.large"}`
    - **ANY_OF**: Multiple options - `{"Field": "memory", "Value": ["8 GiB", "16 GiB"], "Type": "ANY_OF"}`
    - **CONTAINS**: Pattern match - `{"Field": "instanceType", "Value": "m5", "Type": "CONTAINS"}`
    - **NONE_OF**: Exclusion - `{"Field": "instanceType", "Value": ["t2", "m4"], "Type": "NONE_OF"}`

    **CRITICAL: ANY_OF FILTER VALUE LIMITS:**
    - **1024 CHARACTER LIMIT**: Total length of all values in ANY_OF arrays cannot exceed 1024 characters
    - **PROGRESSIVE FILTERING**: Start with minimal qualifying options, expand if needed
    - **EXAMPLE VIOLATION**: `["8 GiB", "16 GiB", "32 GiB", "64 GiB", "96 GiB", "128 GiB", ...]` (TOO LONG)
    - **CORRECT APPROACH**: `["8 GiB", "16 GiB", "32 GiB", "36 GiB", "48 GiB"]` (TARGETED LIST)

    **COMMON USE CASES:**

    **COST OPTIMIZATION - EXHAUSTIVE MINIMUM-FIRST APPROACH:** When users ask for "lowest price", "cheapest", or cost optimization
    - **LOWER = CHEAPER ASSUMPTION**: For cost optimization, assume lower capabilities cost less than higher ones
      * 32 GB storage is cheaper than 300 GB storage
      * 8 GiB RAM is cheaper than 64 GiB RAM
    - **CRITICAL FOR COST QUERIES**: Start IMMEDIATELY above minimum requirement and test ALL options incrementally
    - **EXHAUSTIVE ENUMERATION REQUIRED**: Each storage/memory tier is MUTUALLY EXCLUSIVE - must list each one explicitly
    - **STOP AT REASONABLE UPPER BOUND**: For cost optimization, limit upper bound to 2-3x minimum requirement to avoid expensive options
    - **exclude_free_products**: ESSENTIAL for cost analysis - removes $0.00 reservation placeholders, SQL licensing variants, and special pricing entries that obscure actual billable instances when finding cheapest options
    - Use ANY_OF for efficient multi-option comparison in single API call
    - Multi-attribute capability filtering for minimum requirements
    - Combine CONTAINS + NONE_OF for refined discovery

    **OUTPUT OPTIONS (Response Size & Performance Control):**
    - **PURPOSE**: Transform and optimize API responses for ALL services, especially critical for large services (EC2, RDS)
    - **IMMEDIATE COMBINED APPROACH**: `{"pricing_terms": ["OnDemand"], "product_attributes": ["instanceType", "location", "memory"]}`
    - **ATTRIBUTE DISCOVERY**: Use get_pricing_service_attributes() - same names for filters and output_options
    - **SIZE REDUCTION**: 80%+ reduction with combined pricing_terms + product_attributes
    - **exclude_free_products**: Remove products with $0.00 OnDemand pricing (useful when you know service has paid tiers)
    - **WHEN TO USE**: Always for large services, recommended for all services to improve performance

    **CRITICAL REQUIREMENTS:**
    - **NEVER GUESS VALUES**: Always use get_pricing_attribute_values() to discover valid options
    - **EXHAUSTIVE ENUMERATION**: For cost optimization, list ALL qualifying tiers individually - they are mutually exclusive
    - **USE SPECIFIC FILTERS**: Large services (EC2, RDS) require 2-3 filters minimum
    - **NEVER USE MULTIPLE CALLS**: When ANY_OF can handle it in one call
    - **VERIFY EXISTENCE**: Ensure all filter values exist in the service before querying
    - **FOR "CHEAPEST" QUERIES**: Focus on lower-end options that meet minimum requirements, test incrementally

    **CONSTRAINTS:**
    - **CURRENT PRICING ONLY**: Use get_price_list_urls for historical data
    - **NO SPOT/SAVINGS PLANS**: Only OnDemand and Reserved Instance pricing available
    - **CHARACTER LIMIT**: 100,000 characters default response limit (use output_options to reduce)
    - **REGION AUTO-FILTER**: Region parameter automatically creates regionCode filter

    **ANTI-PATTERNS:**
    - DO NOT make multiple API calls that could be combined with ANY_OF
    - DO NOT build cross-products manually when API can handle combinations
    - DO NOT call get_pricing_service_codes() when service code is already known (e.g., "AmazonEC2")
    - DO NOT use EQUALS without first checking get_pricing_attribute_values()
    - DO NOT skip discovery workflow for any use case
    - DO NOT use broad queries without specific filters on large services
    - DO NOT assume attribute values exist across different services/regions
    - DO NOT skip intermediate tiers: Missing 50GB, 59GB options when testing 32GB → 75GB jump
    - DO NOT set upper bounds too high: Including 500GB+ storage when user needs ≥30GB (wastes character limit)

    **EXAMPLE USE CASES:**

    **1. Cost-Optimized Multi-Attribute Filtering (CORRECT APPROACH):**
    ```python
    # Find cheapest EC2 instances meeting minimum requirements (>= 8 GiB memory, >= 30 GB storage)
    # EXHAUSTIVE ENUMERATION of qualifying tiers - each is mutually exclusive
    filters = [
       {"Field": "memory", "Value": ["8 GiB", "16 GiB", "32 GiB"], "Type": "ANY_OF"},  # All tiers ≥8GB up to reasonable limit
       {"Field": "storage", "Value": ["1 x 32 SSD", "1 x 60 SSD", "1 x 75 NVMe SSD"], "Type": "ANY_OF"},  # All tiers ≥30GB up to reasonable limit
       {"Field": "instanceType", "Value": ["t2", "m4"], "Type": "NONE_OF"},  # Exclude older generations
       {"Field": "tenancy", "Value": "Shared", "Type": "EQUALS"}  # Exclude more expensive dedicated
    ]
    pricing = get_pricing('AmazonEC2', 'us-east-1', filters)
    ```

    **2. Efficient Multi-Region Comparison:**
    ```python
    # Compare same configuration across regions - use region parameter for multi-region
    filters = [{"Field": "instanceType", "Value": "m5.large", "Type": "EQUALS"}]
    pricing = get_pricing('AmazonEC2', ['us-east-1', 'us-west-2', 'eu-west-1'], filters)
    ```

    **3. Large service with output optimization (recommended approach):**
    ```python
    output_options = {"pricing_terms": ["OnDemand"], "product_attributes": ["instanceType", "location"], "exclude_free_products": true}
    pricing = get_pricing('AmazonEC2', 'us-east-1', filters, output_options=output_options)
    ```

    **4. Pattern-Based Discovery with Refinement:**
    ```python
    # Find all Standard storage tiers except expensive ones
    filters = [
        {"Field": "storageClass", "Value": "Standard", "Type": "CONTAINS"},
        {"Field": "storageClass", "Value": ["Standard-IA"], "Type": "NONE_OF"}
    ]
    ```

    **FILTERING STRATEGY:**
    - **Large Services (EC2, RDS)**: ALWAYS use 2-3 specific filters to prevent 200+ record responses
    - **Small Services**: May work with single filter or no filters
    - **Multi-Option Analysis**: Use ANY_OF instead of multiple API calls
    - **Pattern Discovery**: Use CONTAINS for finding families or tiers
    - **Smart Exclusion**: Use NONE_OF for compliance or cost filtering

    **SUCCESS CRITERIA:**
    - Used discovery workflow (skip get_pricing_service_codes() if service known)
    - Applied appropriate filters for the service size
    - Used exact values from get_pricing_attribute_values()
    - Used ANY_OF for multi-option scenarios instead of multiple calls
    - For cost optimization: tested ALL qualifying tiers exhaustively (in a reasonable range)
    """,
)
async def get_pricing(
    ctx: Context,
    service_code: str = SERVICE_CODE_FIELD,
    region: Union[str, List[str]] = REGION_FIELD,
    filters: Optional[List[PricingFilter]] = FILTERS_FIELD,
    max_allowed_characters: int = GET_PRICING_MAX_ALLOWED_CHARACTERS_FIELD,
    output_options: Optional[OutputOptions] = OUTPUT_OPTIONS_FIELD,
    max_results: int = MAX_RESULTS_FIELD,
    next_token: Optional[str] = NEXT_TOKEN_FIELD,
) -> Dict[str, Any]:
    """Get pricing information from AWS Price List API.

    Args:
        service_code: The service code (e.g., 'AmazonES' for OpenSearch, 'AmazonS3' for S3)
        region: AWS region(s) - single region string (e.g., 'us-west-2') or list for multi-region comparison (e.g., ['us-east-1', 'us-west-2'])
        filters: Optional list of filter dictionaries in format {'Field': str, 'Type': str, 'Value': str}
        max_allowed_characters: Optional character limit for response (default: 100,000, use -1 for unlimited)
        output_options: Optional output filtering options to reduce response size
        max_results: Maximum number of results to return per page (default: 100, max: 100)
        next_token: Pagination token from previous response to get next page of results
        ctx: MCP context for logging and state management

    Returns:
        Dictionary containing pricing information from AWS Pricing API. If more results are available,
        the response will include a 'next_token' field that can be used for subsequent requests.
    """
    # Handle Pydantic Field objects when called directly (not through MCP framework)
    if isinstance(filters, FieldInfo):
        filters = filters.default
    if isinstance(max_allowed_characters, FieldInfo):
        max_allowed_characters = max_allowed_characters.default
    if isinstance(output_options, FieldInfo):
        output_options = output_options.default
    if isinstance(max_results, FieldInfo):
        max_results = max_results.default
    if isinstance(next_token, FieldInfo):
        next_token = next_token.default

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
        # Build region filter based on parameter type
        api_filters = [
            {
                'Field': 'regionCode',
                'Type': 'ANY_OF' if isinstance(region, list) else 'TERM_MATCH',
                'Value': ','.join(region) if isinstance(region, list) else region,
            }
        ]

        # Add any additional filters if provided
        if filters:
            api_filters.extend([f.model_dump(by_alias=True) for f in filters])

        # Make the API request
        api_params = {
            'ServiceCode': service_code,
            'Filters': api_filters,
            'MaxResults': max_results,
        }

        # Only include NextToken if it's provided
        if next_token:
            api_params['NextToken'] = next_token

        response = pricing_client.get_products(**api_params)
    except Exception as e:
        return await create_error_response(
            ctx=ctx,
            error_type='api_error',
            message=f'Failed to retrieve pricing data for service "{service_code}" in region "{region}": {str(e)}',
            service_code=service_code,
            region=region,
            suggestion='Verify that the service code and region combination is valid. Use get_service_codes() to get valid service codes.',
        )

    # Check if results are empty
    if not response.get('PriceList'):
        return await create_error_response(
            ctx=ctx,
            error_type='empty_results',
            message=f'No results found for given filters [{filters}], service: "{service_code}", region "{region}"',
            service_code=service_code,
            region=region,
            suggestion='Try these approaches: (1) Verify that the service code is valid. Use get_service_codes() to get valid service codes. (2) Validate region and filter values using get_pricing_attribute_values(). (3) Test with fewer filters to isolate the issue.',
            examples={
                'Example service codes': [
                    'AmazonEC2',
                    'AmazonS3',
                    'AmazonES',
                    'AWSLambda',
                    'AmazonDynamoDB',
                ],
                'Example regions': ['us-east-1', 'eu-west-1', 'ap-south-1'],
            },
        )

    # Apply filtering with error handling
    try:
        price_list = transform_pricing_data(response['PriceList'], output_options)
        total_count = len(price_list)
    except ValueError as e:
        return await create_error_response(
            ctx=ctx,
            error_type='data_processing_error',
            message=f'Failed to process pricing data: {str(e)}',
            service_code=service_code,
            region=region,
        )

    # Check if results exceed the character threshold (unless max_characters is -1 for unlimited)
    if max_allowed_characters != -1:
        # Calculate total character count of the FILTERED response data
        total_characters = sum(len(str(item)) for item in price_list)

        if total_characters > max_allowed_characters:
            return await create_error_response(
                ctx=ctx,
                error_type='result_too_large',
                message=f'Query returned {total_characters:,} characters, exceeding the limit of {max_allowed_characters:,}. Use more specific filters or try output_options={{"pricing_terms": ["OnDemand"]}} to reduce response size.',
                service_code=service_code,
                region=region,
                total_count=total_count,
                total_characters=total_characters,
                max_allowed_characters=max_allowed_characters,
                sample_records=price_list[:3],
                suggestion='Add more specific filters like instanceType, storageClass, deploymentOption, or engineCode to reduce the number of results. For large services like EC2, consider using output_options={"pricing_terms": ["OnDemand"]} to significantly reduce response size by excluding Reserved Instance pricing.',
            )

    # Success response
    logger.info(f'Successfully retrieved {total_count} pricing items for {service_code}')
    await ctx.info(f'Successfully retrieved pricing for {service_code} in {region}')

    result = {
        'status': 'success',
        'service_name': service_code,
        'data': price_list,
        'message': f'Retrieved pricing for {service_code} in {region} from AWS Pricing API',
    }

    # Include next_token if present for pagination
    if 'NextToken' in response:
        result['next_token'] = response['NextToken']

    return result


@mcp.tool(
    name='get_bedrock_patterns',
    description='Get architecture patterns for Amazon Bedrock applications, including component relationships and cost considerations',
)
async def get_bedrock_patterns(ctx: Optional[Context] = None) -> str:
    """Get architecture patterns for Amazon Bedrock applications.

    This tool provides architecture patterns, component relationships, and cost considerations
    for Amazon Bedrock applications. It does not include specific pricing information, which
    should be obtained using get_pricing.

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
    // This should contain pricing data retrieved from get_pricing
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


@mcp.tool(
    name='get_pricing_service_codes',
    description="""Get AWS service codes available in the Price List API.

    **PURPOSE:** Discover which AWS services have pricing information available in the AWS Price List API.

    **WORKFLOW:** This is the starting point for any pricing query. Use this first to find the correct service code.

    **RETURNS:** List of service codes (e.g., 'AmazonEC2', 'AmazonS3', 'AWSLambda') that can be used with other pricing tools.

    **NEXT STEPS:**
    - Use get_pricing_service_attributes() to see what filters are available for a service
    - Use get_pricing() to get actual pricing data for a service

    **NOTE:** Service codes may differ from AWS console names (e.g., 'AmazonES' for OpenSearch, 'AWSLambda' for Lambda).
    """,
)
async def get_pricing_service_codes(ctx: Context) -> Union[List[str], Dict[str, Any]]:
    """Retrieve all available service codes from AWS Price List API.

    Args:
        ctx: MCP context for logging and state management

    Returns:
        List of sorted service codes on success, or error dictionary on failure
    """
    logger.info('Retrieving AWS service codes from Price List API')

    # Create pricing client with error handling
    try:
        pricing_client = create_pricing_client()
    except Exception as e:
        return await create_error_response(
            ctx=ctx,
            error_type='client_creation_failed',
            message=f'Failed to create AWS Pricing client: {str(e)}',
        )

    # Retrieve service codes with error handling
    try:
        service_codes = []
        next_token = None

        # Retrieve all service codes with pagination handling
        while True:
            if next_token:
                response = pricing_client.describe_services(NextToken=next_token)
            else:
                response = pricing_client.describe_services()

            for service in response['Services']:
                service_codes.append(service['ServiceCode'])

            if 'NextToken' in response:
                next_token = response['NextToken']
            else:
                break

    except Exception as e:
        return await create_error_response(
            ctx=ctx,
            error_type='api_error',
            message=f'Failed to retrieve service codes from AWS API: {str(e)}',
            suggestion='Verify AWS credentials and permissions for pricing:DescribeServices action.',
        )

    # Check for empty results
    if not service_codes:
        return await create_error_response(
            ctx=ctx,
            error_type='empty_results',
            message='No service codes returned from AWS Price List API',
        )

    sorted_codes = sorted(service_codes)

    logger.info(f'Successfully retrieved {len(sorted_codes)} service codes')
    await ctx.info(f'Successfully retrieved {len(sorted_codes)} service codes')

    return sorted_codes


@mcp.tool(
    name='get_pricing_service_attributes',
    description="""Get filterable attributes available for an AWS service in the Pricing API.

    **PURPOSE:** Discover what pricing dimensions (filters) are available for a specific AWS service.

    **WORKFLOW:** Use this after get_pricing_service_codes() to see what filters you can apply to narrow down pricing queries.

    **REQUIRES:** Service code from get_pricing_service_codes() (e.g., 'AmazonEC2', 'AmazonRDS').

    **RETURNS:** List of attribute names (e.g., 'instanceType', 'location', 'storageClass') that can be used as filters.

    **NEXT STEPS:**
    - Use get_pricing_attribute_values() to see valid values for each attribute
    - Use these attributes in get_pricing() filters to get specific pricing data

    **EXAMPLE:** For 'AmazonRDS' you might get ['engineCode', 'instanceType', 'deploymentOption', 'location'].
    """,
)
async def get_pricing_service_attributes(
    ctx: Context, service_code: str = SERVICE_CODE_FIELD
) -> Union[List[str], Dict[str, Any]]:
    """Retrieve all available attributes for a specific AWS service.

    Args:
        service_code: The service code to query (e.g., 'AmazonEC2', 'AmazonS3')
        ctx: MCP context for logging and state management

    Returns:
        List of sorted attribute name strings on success, or error dictionary on failure
    """
    logger.info(f'Retrieving attributes for AWS service: {service_code}')

    # Create pricing client with error handling
    try:
        pricing_client = create_pricing_client()
    except Exception as e:
        return await create_error_response(
            ctx=ctx,
            error_type='client_creation_failed',
            message=f'Failed to create AWS Pricing client: {str(e)}',
            service_code=service_code,
        )

    # Get service attributes with error handling
    try:
        response = pricing_client.describe_services(ServiceCode=service_code)
    except Exception as e:
        return await create_error_response(
            ctx=ctx,
            error_type='api_error',
            message=f'Failed to retrieve attributes for service "{service_code}": {str(e)}',
            service_code=service_code,
            suggestion='Verify that the service code is valid and AWS credentials have the required pricing:DescribeServices permissions. Use get_service_codes() to get valid service codes.',
        )

    # Check if service was found
    if not response.get('Services'):
        return await create_error_response(
            ctx=ctx,
            error_type='service_not_found',
            message=f'Service "{service_code}" was not found. Please verify the service code is correct.',
            service_code=service_code,
            suggestion='Use get_service_codes() to retrieve a list of all available AWS service codes.',
            examples={
                'OpenSearch': 'AmazonES',
                'Lambda': 'AWSLambda',
                'DynamoDB': 'AmazonDynamoDB',
                'EC2': 'AmazonEC2',
                'S3': 'AmazonS3',
            },
        )

    # Extract attribute names
    attributes = []
    for attr in response['Services'][0].get('AttributeNames', []):
        attributes.append(attr)

    # Check for empty results
    if not attributes:
        return await create_error_response(
            ctx=ctx,
            error_type='empty_results',
            message=f'Service "{service_code}" exists but has no filterable attributes available.',
            service_code=service_code,
            suggestion='This service may not support attribute-based filtering, or there may be a temporary issue. Try using get_pricing() without filters.',
        )

    sorted_attributes = sorted(attributes)

    logger.info(f'Successfully retrieved {len(sorted_attributes)} attributes for {service_code}')
    await ctx.info(
        f'Successfully retrieved {len(sorted_attributes)} attributes for {service_code}'
    )

    return sorted_attributes


class AttributeValuesError(Exception):
    """Custom exception for attribute values retrieval errors."""

    def __init__(
        self, error_type: str, message: str, service_code: str, attribute_name: str, **kwargs
    ):
        """Init AttributeValuesError."""
        self.error_type = error_type
        self.message = message
        self.service_code = service_code
        self.attribute_name = attribute_name
        self.extra_fields = kwargs
        super().__init__(message)


async def _get_single_attribute_values(
    pricing_client,
    service_code: str,
    attribute_name: str,
) -> List[str]:
    """Helper function to retrieve values for a single attribute.

    Args:
        pricing_client: AWS pricing client instance
        service_code: The service code to query
        attribute_name: The attribute name to get values for

    Returns:
        List of sorted attribute values on success

    Raises:
        AttributeValuesError: When API calls fail or no values are found
    """
    try:
        # Get attribute values with pagination handling
        values = []
        next_token = None

        while True:
            if next_token:
                response = pricing_client.get_attribute_values(
                    ServiceCode=service_code, AttributeName=attribute_name, NextToken=next_token
                )
            else:
                response = pricing_client.get_attribute_values(
                    ServiceCode=service_code, AttributeName=attribute_name
                )

            for attr_value in response.get('AttributeValues', []):
                if 'Value' in attr_value:
                    values.append(attr_value['Value'])

            if 'NextToken' in response:
                next_token = response['NextToken']
            else:
                break

    except Exception as e:
        raise AttributeValuesError(
            error_type='api_error',
            message=f'Failed to retrieve values for attribute "{attribute_name}" of service "{service_code}": {str(e)}',
            service_code=service_code,
            attribute_name=attribute_name,
            suggestion='Verify that both the service code and attribute name are valid. Use get_service_codes() to get valid service codes and get_service_attributes() to get valid attributes for a service.',
        )

    # Check if no values were found
    if not values:
        raise AttributeValuesError(
            error_type='no_attribute_values_found',
            message=f'No values found for attribute "{attribute_name}" of service "{service_code}". This could be due to an invalid service code or an invalid attribute name for this service.',
            service_code=service_code,
            attribute_name=attribute_name,
            suggestion='Use get_service_codes() to verify the service code and get_service_attributes() to verify the attribute name for this service.',
            examples={
                'Common service codes': ['AmazonEC2', 'AmazonS3', 'AmazonES', 'AWSLambda'],
                'Common attributes': [
                    'instanceType',
                    'location',
                    'storageClass',
                    'engineCode',
                ],
            },
        )

    return sorted(values)


@mcp.tool(
    name='get_pricing_attribute_values',
    description="""Get valid values for pricing filter attributes.

    **PURPOSE:** Discover what values are available for specific pricing filter attributes of an AWS service.

    **WORKFLOW:** Use this after get_pricing_service_attributes() to see valid values for each filter attribute.

    **REQUIRES:**
    - Service code from get_pricing_service_codes() (e.g., 'AmazonEC2', 'AmazonRDS')
    - List of attribute names from get_pricing_service_attributes() (e.g., ['instanceType', 'location'])

    **RETURNS:** Dictionary mapping attribute names to their valid values.

    **EXAMPLE RETURN:**
    ```
    {
        'instanceType': ['t2.micro', 't3.medium', 'm5.large', ...],
        'location': ['US East (N. Virginia)', 'EU (London)', ...]
    }
    ```

    **NEXT STEPS:** Use these values in get_pricing() filters to get specific pricing data.

    **ERROR HANDLING:** Uses "all-or-nothing" approach - if any attribute fails, the entire operation fails.

    **EXAMPLES:**
    - Single attribute: ['instanceType'] returns {'instanceType': ['t2.micro', 't3.medium', ...]}
    - Multiple attributes: ['instanceType', 'location'] returns both mappings
    """,
)
async def get_pricing_attribute_values(
    ctx: Context,
    service_code: str = SERVICE_CODE_FIELD,
    attribute_names: List[str] = ATTRIBUTE_NAMES_FIELD,
) -> Union[Dict[str, List[str]], Dict[str, Any]]:
    """Retrieve all possible values for specific attributes of an AWS service.

    Args:
        service_code: The service code to query (e.g., 'AmazonEC2', 'AmazonS3')
        attribute_names: List of attribute names to get values for (e.g., ['instanceType', 'location'])
        ctx: MCP context for logging and state management

    Returns:
        Dictionary mapping attribute names to sorted lists of values on success, or error dictionary on failure
    """
    if not attribute_names:
        return await create_error_response(
            ctx=ctx,
            error_type='empty_attribute_list',
            message='No attribute names provided. Please provide at least one attribute name.',
            service_code=service_code,
            attribute_names=attribute_names,
            suggestion='Use get_pricing_service_attributes() to get valid attribute names for this service.',
        )

    logger.info(
        f'Retrieving values for {len(attribute_names)} attributes of service: {service_code}'
    )

    # Create pricing client with error handling
    try:
        pricing_client = create_pricing_client()
    except Exception as e:
        return await create_error_response(
            ctx=ctx,
            error_type='client_creation_failed',
            message=f'Failed to create AWS Pricing client: {str(e)}',
            service_code=service_code,
            attribute_names=attribute_names,
        )

    # Process each attribute - all-or-nothing approach
    result = {}
    for attribute_name in attribute_names:
        logger.debug(f'Processing attribute: {attribute_name}')

        try:
            values_result = await _get_single_attribute_values(
                pricing_client, service_code, attribute_name
            )
            # Success - add to result
            result[attribute_name] = values_result
        except AttributeValuesError as e:
            # If any attribute fails, return error for entire operation
            return await create_error_response(
                ctx=ctx,
                error_type=e.error_type,
                message=f'Failed to retrieve values for attribute "{attribute_name}": {e.message}',
                service_code=e.service_code,
                attribute_name=e.attribute_name,
                failed_attribute=attribute_name,
                requested_attributes=attribute_names,
                **e.extra_fields,
            )

    total_values = sum(len(values) for values in result.values())
    logger.info(
        f'Successfully retrieved {total_values} total values for {len(attribute_names)} attributes of service {service_code}'
    )
    await ctx.info(
        f'Successfully retrieved values for {len(attribute_names)} attributes of service {service_code}'
    )

    return result


@mcp.tool(
    name='get_price_list_urls',
    description="""Get download URLs for bulk pricing data files.

    **PURPOSE:** Access complete AWS pricing datasets as downloadable files for historical analysis and bulk processing.

    **WORKFLOW:** Use this for historical pricing analysis or bulk data processing when current pricing from get_pricing() isn't sufficient.

    **REQUIRES:**
    - Service code from get_pricing_service_codes() (e.g., 'AmazonEC2', 'AmazonS3')
    - AWS region (e.g., 'us-east-1', 'eu-west-1')
    - Optional: effective_date for historical pricing (default: current date)

    **RETURNS:** Dictionary with download URLs for different formats:
    - 'csv': Direct download URL for CSV format
    - 'json': Direct download URL for JSON format

    **USE CASES:**
    - Historical pricing analysis (get_pricing() only provides current pricing)
    - Bulk data processing without repeated API calls
    - Offline analysis of complete pricing datasets
    - Savings Plans analysis across services

    **FILE PROCESSING:**
    - CSV files: Lines 1-5 are metadata, Line 6 contains headers, Line 7+ contains pricing data
    - Use `tail -n +7 pricing.csv | grep "t3.medium"` to filter data
    """,
)
async def get_price_list_urls(
    ctx: Context,
    service_code: str = SERVICE_CODE_FIELD,
    region: str = REGION_FIELD,
    effective_date: Optional[str] = EFFECTIVE_DATE_FIELD,
) -> Dict[str, Any]:
    """Get URLs to download bulk pricing data from AWS Price List API for all available formats.

    This tool combines the list-price-lists and get-price-list-file-url API calls
    to provide download URLs for all available file formats.

    Args:
        ctx: MCP context for logging and state management
        service_code: AWS service code (e.g., 'AmazonEC2', 'AmazonS3')
        region: AWS region (e.g., 'us-east-1')
        effective_date: Effective date in 'YYYY-MM-DD HH:MM' format (default: current timestamp)

    Returns:
        Dictionary containing download URLs for all available formats
    """
    logger.info(f'Getting price list file URLs for {service_code} in {region}')

    # Set effective date to current timestamp if not provided
    if not effective_date:
        effective_date = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
        logger.debug(f'Using current timestamp for effective_date: {effective_date}')

    # Determine currency based on region
    currency = get_currency_for_region(region)
    logger.debug(f'Using currency {currency} for region {region}')

    try:
        # Create pricing client
        pricing_client = create_pricing_client()
    except Exception as e:
        return await create_error_response(
            ctx=ctx,
            error_type='client_creation_failed',
            message=f'Failed to create AWS Pricing client: {str(e)}',
            service_code=service_code,
            region=region,
        )

    # Step 1: List price lists to find the appropriate ARN
    logger.info(
        f'Searching for price list: service={service_code}, region={region}, date={effective_date}, currency={currency}'
    )

    try:
        list_response = pricing_client.list_price_lists(
            ServiceCode=service_code,
            EffectiveDate=effective_date,
            RegionCode=region,
            CurrencyCode=currency,
        )
    except Exception as e:
        return await create_error_response(
            ctx=ctx,
            error_type='list_price_lists_failed',
            message=f'Failed to list price lists for service "{service_code}" in region "{region}": {str(e)}',
            service_code=service_code,
            region=region,
            effective_date=effective_date,
            currency=currency,
            suggestion='Verify that the service code and region combination is valid. Use get_service_codes() to get valid service codes.',
        )

    # Check if any price lists were found
    price_lists = list_response.get('PriceLists', [])
    if not price_lists:
        return await create_error_response(
            ctx=ctx,
            error_type='no_price_list_found',
            message=f'No price lists found for service "{service_code}" in region "{region}" for date "{effective_date}" with currency "{currency}"',
            service_code=service_code,
            region=region,
            effective_date=effective_date,
            currency=currency,
            suggestion='Try using a different effective date or verify the service code and region combination using get_service_codes() and get_attribute_values().',
        )

    # Get the first (most recent) price list
    price_list = price_lists[0]
    price_list_arn = price_list['PriceListArn']
    supported_formats = price_list.get('FileFormats', [])
    logger.info(f'Found price list ARN: {price_list_arn} with formats: {supported_formats}')

    if not supported_formats:
        return await create_error_response(
            ctx=ctx,
            error_type='no_formats_available',
            message=f'Price list found but no file formats are available for service "{service_code}"',
            service_code=service_code,
            region=region,
            price_list_arn=price_list_arn,
        )

    # Step 2: Get URLs for all available formats
    result = {'arn': price_list_arn, 'urls': {}}

    for file_format in supported_formats:
        format_key = file_format.lower()
        logger.info(f'Getting file URL for format: {file_format}')

        try:
            url_response = pricing_client.get_price_list_file_url(
                PriceListArn=price_list_arn, FileFormat=file_format.upper()
            )

            download_url = url_response.get('Url')
            if not download_url:
                return await create_error_response(
                    ctx=ctx,
                    error_type='empty_url_response',
                    message=f'AWS API returned empty URL for format "{file_format}"',
                    service_code=service_code,
                    region=region,
                    price_list_arn=price_list_arn,
                    file_format=format_key,
                    suggestion='This may be a temporary AWS service issue. Try again in a few minutes.',
                )

            result['urls'][format_key] = download_url
            logger.debug(f'Successfully got URL for format {file_format}')

        except Exception as e:
            return await create_error_response(
                ctx=ctx,
                error_type='format_url_failed',
                message=f'Failed to get download URL for format "{file_format}": {str(e)}',
                service_code=service_code,
                region=region,
                price_list_arn=price_list_arn,
                file_format=format_key,
                suggestion='This format may not be available for this service. Check supported_formats in the price list response.',
            )

    logger.info(
        f'Successfully retrieved {len(result["urls"])} price list file URLs for {service_code}'
    )
    await ctx.info(f'Successfully retrieved price list file URLs for {service_code}')

    return result['urls']


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()
