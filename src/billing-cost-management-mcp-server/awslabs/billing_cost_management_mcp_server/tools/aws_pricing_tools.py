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

"""AWS Pricing tools for the AWS Billing and Cost Management MCP server.

Updated to use shared utility functions.
"""

from ..utilities.aws_service_base import format_response, handle_aws_error

# Import operation handlers from local module
from .aws_pricing_operations import (
    get_attribute_values,
    get_pricing_from_api,
    get_service_attributes,
    get_service_codes,
)
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


aws_pricing_server = FastMCP(
    name='aws-pricing-tools', instructions='Tools for working with AWS Pricing API'
)


@aws_pricing_server.tool(
    name='aws-pricing',
    description="""Comprehensive AWS pricing analysis tool that provides access to AWS service pricing information and cost analysis capabilities.

This tool supports four main operations:
1. get_service_codes: Get a comprehensive list of AWS service codes from the AWS Price List API
2. get_service_attributes: Get filterable attributes for a specific AWS service's pricing
3. get_attribute_values: Get all valid values for a specific attribute of an AWS service
4. get_pricing_from_api: Get detailed pricing information from AWS Price List API with optional filters

USE THE OPERATIONS IN THIS ORDER:
1. get_service_codes: Entry point - discover available AWS services and their unique service codes. Note that service codes may not match your expectations, so it's best to get service codes first.
2. get_service_attributes: Second step - understand which dimensions affect pricing for a chosen service
3. get_attribute_values: Third step - get possible values you can use in pricing filters
4. get_pricing_from_api: Final step - retrieve actual pricing data based on service and filters
**If you deviate from this order of operations, you will struggle to form the correct filters, and you will not get results from the API**

IMPORTANT GUIDELINES:
- When retrieving foundation model pricing, always use the latest models for comparison
- For database compatibility with services, only include confirmed supported databases
- Providing less information is better than giving incorrect information
- Price list APIs can return large data volumes. Use narrower filters to retrieve less data when possible
- Service codes often differ from AWS console names (e.g., 'AmazonES' for OpenSearch)

ARGS:
      ctx: The MCP context object
      operation: The pricing operation to perform ('get_service_codes', 'get_service_attributes', 'get_attribute_values', 'get_pricing_from_api')
      service_code: AWS service code (e.g., 'AmazonEC2', 'AmazonS3', 'AmazonES'). Required for get_service_attributes, get_attribute_values, and get_pricing_from_api operations.
      attribute_name: Attribute name (e.g., 'instanceType', 'location', 'storageClass'). Required for get_attribute_values operation.
      region: AWS region (e.g., 'us-east-1', 'us-west-2', 'eu-west-1'). Required for get_pricing_from_api operation.
      filters: Optional filters for pricing queries. Format: {'instanceType': 't3.medium', 'location': 'US East (N. Virginia)'}

RETURNS:
        Dict containing the pricing information

SUPPORTED AWS PRICING API REGIONS:
- Classic partition: us-east-1, eu-central-1, ap-southeast-1
- China partition: cn-northwest-1
The tool automatically maps your region to the nearest pricing endpoint.""",
)
async def aws_pricing(
    ctx: Context,
    operation: str,
    service_code: Optional[str] = None,
    attribute_name: Optional[str] = None,
    region: Optional[str] = None,
    filters: Optional[str] = None,
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    """AWS pricing analysis tool.

    Args:
        ctx: The MCP context object
        operation: The pricing operation to perform ('get_service_codes', 'get_service_attributes', 'get_attribute_values', 'get_pricing_from_api')
        service_code: AWS service code (e.g., 'AmazonEC2', 'AmazonS3', 'AmazonES'). Required for get_service_attributes, get_attribute_values, and get_pricing_from_api operations.
        attribute_name: Attribute name (e.g., 'instanceType', 'location', 'storageClass'). Required for get_attribute_values operation.
        region: AWS region (e.g., 'us-east-1', 'us-west-2', 'eu-west-1'). Required for get_pricing_from_api operation.
        filters: Optional filters for pricing queries as a JSON string. Format: '{"instanceType": "t3.medium", "location": "US East (N. Virginia)"}'
        max_results: Maximum number of results to return (optional)

    Returns:
        Dict containing the pricing information
    """
    try:
        await ctx.info(f'AWS Pricing operation: {operation}')

        if operation == 'get_service_codes':
            return await get_service_codes(ctx, max_results=max_results)

        elif operation == 'get_service_attributes':
            if not service_code:
                return format_response(
                    'error',
                    {'message': 'service_code is required for get_service_attributes operation'},
                )
            return await get_service_attributes(ctx, service_code)

        elif operation == 'get_attribute_values':
            if not service_code or not attribute_name:
                return format_response(
                    'error',
                    {
                        'message': 'service_code and attribute_name are required for get_attribute_values operation'
                    },
                )
            return await get_attribute_values(
                ctx, service_code, attribute_name, max_results=max_results
            )

        elif operation == 'get_pricing_from_api':
            if not service_code or not region:
                return format_response(
                    'error',
                    {
                        'message': 'service_code and region are required for get_pricing_from_api operation'
                    },
                )
            return await get_pricing_from_api(
                ctx, service_code, region, filters, max_results=max_results
            )

        else:
            return format_response(
                'error',
                {
                    'message': f'Unknown operation: {operation}. Supported operations: get_service_codes, get_service_attributes, get_attribute_values, get_pricing_from_api'
                },
            )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, operation, 'AWS Pricing')
