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

"""AWS Pricing tool for the AWS Billing and Cost Management MCP server.

This module provides comprehensive AWS pricing analysis capabilities through the
AWS Price List API, with support for multi-account access.
"""

from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional
from .aws_pricing_operations import (
    get_service_codes,
    get_service_attributes,
    get_attribute_values,
    get_pricing_from_api,
)


# Create the FastMCP server instance
aws_pricing_server = FastMCP(
    name='aws-pricing-tools',
    instructions='Tools for working with AWS Pricing API'
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

MULTI-ACCOUNT SUPPORT:
- Optionally specify account_id parameter to query pricing from a different AWS account
- If account_id is not provided, uses the current account where the MCP server is running
- Requires cross-account IAM role 'MCPServerCrossAccountRole' in target accounts
- Region defaults to us-east-1 but can be overridden

ARGS:
      ctx: The MCP context object
      operation: The pricing operation to perform ('get_service_codes', 'get_service_attributes', 'get_attribute_values', 'get_pricing_from_api')
      service_code: AWS service code (e.g., 'AmazonEC2', 'AmazonS3', 'AmazonES'). Required for get_service_attributes, get_attribute_values, and get_pricing_from_api operations.
      attribute_name: Attribute name (e.g., 'instanceType', 'location', 'storageClass'). Required for get_attribute_values operation.
      region: AWS region (e.g., 'us-east-1', 'us-west-2', 'eu-west-1'). Required for get_pricing_from_api operation.
      filters: Optional filters for pricing queries. Format: {'instanceType': 't3.medium', 'location': 'US East (N. Virginia)'}
      account_id: Target AWS account ID (optional, uses current account if not provided)

RETURNS:
        Dict containing the pricing information

SUPPORTED AWS PRICING API REGIONS:
- Classic partition: us-east-1, eu-central-1, ap-southeast-1
- China partition: cn-northwest-1
The tool automatically maps your region to the nearest pricing endpoint."""
)
async def aws_pricing(
    ctx: Context,
    operation: str,
    service_code: Optional[str] = None,
    attribute_name: Optional[str] = None,
    region: str = 'us-east-1',
    filters: Optional[str] = None,
    max_results: Optional[int] = None,
    account_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle AWS Pricing API operations.

    This tool provides access to AWS service pricing information and cost analysis
    capabilities, with support for querying pricing across multiple AWS accounts.

    Supported operations:
    1. get_service_codes: Get comprehensive list of AWS service codes
    2. get_service_attributes: Get filterable attributes for a service's pricing
    3. get_attribute_values: Get all valid values for a specific attribute
    4. get_pricing_from_api: Get detailed pricing information with optional filters

    Multi-account support:
    - Optionally specify account_id parameter to query pricing from different AWS account
    - If account_id is not provided, uses the current account where server is running
    - Requires cross-account IAM role 'MCPServerCrossAccountRole' in target accounts

    Args:
        ctx: MCP context object
        operation: The pricing operation to perform
        service_code: AWS service code (required for some operations)
        attribute_name: Attribute name (required for get_attribute_values)
        region: AWS region (default: us-east-1)
        filters: Optional filters for pricing queries (JSON string)
        max_results: Maximum number of results to return
        account_id: Target AWS account ID (optional)

    Returns:
        Dict containing the pricing information with account tracking

    Examples:
        # Get all service codes
        {"operation": "get_service_codes"}

        # Get all service codes for specific account
        {"operation": "get_service_codes", "account_id": "123456789012"}

        # Get attributes for EC2
        {"operation": "get_service_attributes", "service_code": "AmazonEC2"}

        # Get instance types
        {"operation": "get_attribute_values", "service_code": "AmazonEC2", "attribute_name": "instanceType"}

        # Get EC2 pricing
        {"operation": "get_pricing_from_api", "service_code": "AmazonEC2", "region": "us-east-1"}

        # Get EC2 pricing with filters
        {
            "operation": "get_pricing_from_api",
            "service_code": "AmazonEC2",
            "region": "us-east-1",
            "filters": "{\\"instanceType\\": \\"t3.medium\\", \\"location\\": \\"US East (N. Virginia)\\"}"
        }

        # Get pricing from different account
        {
            "operation": "get_pricing_from_api",
            "service_code": "AmazonS3",
            "region": "us-west-2",
            "account_id": "123456789012"
        }
    """
    # Route to appropriate operation
    if operation == 'get_service_codes':
        return await get_service_codes(
            ctx=ctx,
            max_results=max_results,
            account_id=account_id,
            region=region,
        )

    elif operation == 'get_service_attributes':
        if not service_code:
            return {
                'status': 'error',
                'data': {'message': 'service_code is required for get_service_attributes operation'},
            }
        return await get_service_attributes(
            ctx=ctx,
            service_code=service_code,
            account_id=account_id,
            region=region,
        )

    elif operation == 'get_attribute_values':
        if not service_code:
            return {
                'status': 'error',
                'data': {'message': 'service_code is required for get_attribute_values operation'},
            }
        if not attribute_name:
            return {
                'status': 'error',
                'data': {'message': 'attribute_name is required for get_attribute_values operation'},
            }
        return await get_attribute_values(
            ctx=ctx,
            service_code=service_code,
            attribute_name=attribute_name,
            max_results=max_results,
            account_id=account_id,
            region=region,
        )

    elif operation == 'get_pricing_from_api':
        if not service_code:
            return {
                'status': 'error',
                'data': {'message': 'service_code is required for get_pricing_from_api operation'},
            }
        return await get_pricing_from_api(
            ctx=ctx,
            service_code=service_code,
            region=region,
            filters=filters,
            max_results=max_results,
            account_id=account_id,
        )

    else:
        return {
            'status': 'error',
            'data': {
                'message': f'Unknown operation: {operation}',
                'supported_operations': [
                    'get_service_codes',
                    'get_service_attributes',
                    'get_attribute_values',
                    'get_pricing_from_api',
                ],
            },
        }