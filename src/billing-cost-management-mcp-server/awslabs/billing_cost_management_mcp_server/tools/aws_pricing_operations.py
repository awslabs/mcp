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

"""AWS Pricing operations for the AWS Billing and Cost Management MCP server.

This module contains the individual operation handlers for the AWS Pricing tool.
Updated to use shared utility functions.
"""

import json
import os
from ..utilities.aws_service_base import (
    PageSpec,
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_items,
    parse_json,
    with_pagination,
)
from ..utilities.logging_utils import get_context_logger
from ..utilities.sql_utils import convert_response_if_needed
from fastmcp import Context
from typing import Any, Dict, Optional


AWS_PRICING_SERVICE_NAME = 'AWS Pricing'

PRICING_API_REGIONS = {
    'classic': ['us-east-1', 'eu-central-1', 'ap-south-1'],
    'china': ['cn-northwest-1'],
}


def get_pricing_region(requested_region: Optional[str] = None) -> str:
    """Determine the appropriate AWS Pricing API region.

    The AWS Pricing API is only available in specific regions:
    - Classic partition: us-east-1, eu-central-1, ap-south-1
    - China partition: cn-northwest-1

    Args:
        requested_region: The AWS region requested by the user (default: None)

    Returns:
        str: The closest AWS Pricing API region
    """
    if not requested_region:
        requested_region = os.environ.get('AWS_REGION', 'us-east-1')

    all_pricing_regions = PRICING_API_REGIONS['classic'] + PRICING_API_REGIONS['china']
    if requested_region in all_pricing_regions:
        return requested_region

    if requested_region.startswith('cn-'):
        pricing_region = 'cn-northwest-1'
    elif requested_region.startswith(('eu-', 'me-', 'af-')):
        pricing_region = 'eu-central-1'
    elif requested_region.startswith('ap-'):
        pricing_region = 'ap-south-1'
    else:
        pricing_region = 'us-east-1'

    return pricing_region


def create_pricing_client() -> Any:
    """Create a Pricing API client using the appropriate regional endpoint."""
    return create_aws_client('pricing', get_pricing_region())


# DescribeServices (no ServiceCode) lists every service, up to 100 per page.
DESCRIBE_SERVICES_PAGE_SPEC = PageSpec(
    result_key='Services',
    token_param='NextToken',
    token_key_in_response='NextToken',
    page_max=100,
    page_size_param='MaxResults',
)


async def get_service_codes(
    ctx: Context, max_items: Optional[int] = None, next_token: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve the service codes from AWS Price List API.

    Uses shared utilities for client creation and response formatting.

    Args:
        ctx: MCP context
        max_items: Most service codes to return. None fetches every page.
        next_token: Continuation token from a previous response.

    Returns:
        Dict containing service codes and a ``pagination`` block
    """
    try:
        await ctx.info('Retrieving AWS service codes from Price List API')

        # Create pricing client using shared utility
        pricing_client = create_pricing_client()

        services, _, pagination = await paginate_aws_items(
            ctx,
            'DescribeServices',
            pricing_client.describe_services,
            {},
            DESCRIBE_SERVICES_PAGE_SPEC,
            max_items=max_items,
            next_token=next_token,
        )
        # Kept in the service's order. It is the same across pages in practice, though the
        # API reference does not document an order; sorting each page would break it.
        service_codes = [service['ServiceCode'] for service in services]

        # Use shared format_response utility
        return format_response(
            'success',
            with_pagination(
                {
                    'service_codes': service_codes,
                    'message': f'Successfully retrieved {len(service_codes)} AWS service codes',
                },
                pagination,
            ),
        )

    except Exception as e:
        # Route through the shared handler so the response carries a top-level
        # error_type + operation (consistent structured error shape), while
        # keeping the legacy `data.message` payload for backward compatibility.
        classified = await handle_aws_error(ctx, e, 'get_service_codes', AWS_PRICING_SERVICE_NAME)
        classified['data'] = {'message': f'Error retrieving service codes: {str(e)}'}
        return classified


async def get_service_attributes(ctx: Context, service_code: str) -> Dict[str, Any]:
    """Retrieve all available attributes for a specific AWS service.

    Args:
        ctx: MCP context
        service_code: AWS service code (e.g., 'AmazonEC2', 'AmazonS3')

    Returns:
        Dict containing service attributes
    """
    try:
        await ctx.info(f'Retrieving attributes for service: {service_code}')

        # Create pricing client using shared utility
        pricing_client = create_pricing_client()

        # Make API call
        response = pricing_client.describe_services(ServiceCode=service_code)

        # Check if service exists
        if not response.get('Services'):
            # Not an exception, but still an error response. Emit a top-level
            # error_type + operation (consistent structured error shape) while
            # keeping the legacy `data.message` payload for compatibility.
            message = f'No service found with code: {service_code}'
            return {
                **format_response('error', {'message': message}),
                'service': AWS_PRICING_SERVICE_NAME,
                'operation': 'get_service_attributes',
                'error_type': 'no_results',
                'message': message,
            }

        # Extract attributes
        attributes = []
        for attr in response['Services'][0].get('AttributeNames', []):
            attributes.append(attr)

        # Sort for consistent output
        sorted_attributes = sorted(attributes)

        # Use shared format_response utility
        return format_response(
            'success',
            {
                'service_code': service_code,
                'attributes': sorted_attributes,
                'message': f'Successfully retrieved {len(sorted_attributes)} attributes for {service_code}',
            },
        )

    except Exception as e:
        # Route through the shared handler so the response carries a top-level
        # error_type + operation (consistent structured error shape), while
        # keeping the legacy `data.message` payload for backward compatibility.
        classified = await handle_aws_error(
            ctx, e, 'get_service_attributes', AWS_PRICING_SERVICE_NAME
        )
        classified['data'] = {
            'message': f'Failed to retrieve attributes for service {service_code}: {str(e)}'
        }
        return classified


# GetAttributeValues returns up to 10,000 values per page.
GET_ATTRIBUTE_VALUES_PAGE_SPEC = PageSpec(
    result_key='AttributeValues',
    token_param='NextToken',
    token_key_in_response='NextToken',
    page_max=10000,
    page_size_param='MaxResults',
)


async def get_attribute_values(
    ctx: Context,
    service_code: str,
    attribute_name: str,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve the possible values for a specific attribute of an AWS service.

    Args:
        ctx: MCP context
        service_code: AWS service code
        attribute_name: Service attribute name
        max_items: Most values to return. None fetches every page.
        next_token: Continuation token from a previous response.

    Returns:
        Dict containing attribute values and a ``pagination`` block
    """
    try:
        await ctx.info(
            f"Retrieving values for attribute '{attribute_name}' of service '{service_code}'"
        )

        # Create pricing client using shared utility
        pricing_client = create_pricing_client()

        attribute_values, _, pagination = await paginate_aws_items(
            ctx,
            'GetAttributeValues',
            pricing_client.get_attribute_values,
            {'ServiceCode': service_code, 'AttributeName': attribute_name},
            GET_ATTRIBUTE_VALUES_PAGE_SPEC,
            max_items=max_items,
            next_token=next_token,
        )
        # Kept in the service's order. It is the same across pages in practice, though the
        # API reference does not document an order; sorting each page would break it.
        values = [item['Value'] for item in attribute_values if 'Value' in item]

        # Use shared format_response utility
        return format_response(
            'success',
            with_pagination(
                {
                    'service_code': service_code,
                    'attribute_name': attribute_name,
                    'values': values,
                    'message': f'Successfully retrieved {len(values)} values for attribute {attribute_name} of service {service_code}',
                },
                pagination,
            ),
        )

    except Exception as e:
        # Route through the shared handler so the response carries a top-level
        # error_type + operation (consistent structured error shape), while
        # keeping the legacy `data.message` payload for backward compatibility.
        classified = await handle_aws_error(
            ctx, e, 'get_attribute_values', AWS_PRICING_SERVICE_NAME
        )
        classified['data'] = {
            'message': f'Failed to retrieve values for attribute {attribute_name} of service {service_code}: {str(e)}'
        }
        return classified


# GetProducts returns up to 100 products per page.
GET_PRODUCTS_PAGE_SPEC = PageSpec(
    result_key='PriceList',
    token_param='NextToken',
    token_key_in_response='NextToken',
    page_max=100,
    page_size_param='MaxResults',
)


async def get_pricing_from_api(
    ctx: Context,
    service_code: str,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Get pricing information from AWS Price List API.

    Args:
        ctx: MCP context
        service_code: AWS service code
        filters: Optional filters as JSON string
        max_items: Most products to return. None fetches every page.
        next_token: Continuation token from a previous response.

    Returns:
        Dict containing pricing data and a ``pagination`` block
    """
    try:
        await ctx.info(f"Retrieving pricing data for service '{service_code}'")

        # Create pricing client using shared utility
        pricing_client = create_pricing_client()

        # Process filters
        api_filters = []
        if filters:
            # Parse JSON using shared utility
            filters_dict = parse_json(filters, 'filters')
            if filters_dict:
                # Format: {"volumeType": "Standard", "storageClass": "General Purpose"}
                for field, value in filters_dict.items():
                    if value is not None:
                        filter_dict = {'Field': field, 'Type': 'TERM_MATCH', 'Value': value}
                        api_filters.append(filter_dict)

                await ctx.info(f'Applied {len(api_filters)} filters')

        all_price_list, _, pagination = await paginate_aws_items(
            ctx,
            'GetProducts',
            pricing_client.get_products,
            {'ServiceCode': service_code, 'Filters': api_filters},
            GET_PRODUCTS_PAGE_SPEC,
            max_items=max_items,
            next_token=next_token,
        )

        # Handle no results. This is a genuine "no data" case rather than an
        # exception, but it is still an error response: emit a top-level
        # error_type + operation (consistent structured error shape) while
        # keeping the legacy `data` payload (message + examples) for
        # backward compatibility. A partial result (a later page failed) is not
        # "no data", so it falls through with its pagination block.
        # A continuation (next_token) that reaches an empty last page is not a bad service code.
        if not all_price_list and pagination['complete_dataset'] and not next_token:
            message = f'The service code "{service_code}" did not return any pricing data. AWS service codes typically follow patterns like "AmazonS3", "AmazonEC2", "AmazonES", etc. Please check the exact service code and try again.'
            examples = {
                'OpenSearch': 'AmazonES',
                'Lambda': 'AWSLambda',
                'DynamoDB': 'AmazonDynamoDB',
                'Bedrock': 'AmazonBedrock',
            }
            return {
                **format_response('error', {'message': message, 'examples': examples}),
                'service': AWS_PRICING_SERVICE_NAME,
                'operation': 'get_pricing_from_api',
                'error_type': 'no_results',
                'message': message,
            }

        # Create response with raw data
        raw_response = with_pagination(
            {
                'service_code': service_code,
                'filter_count': len(api_filters),
                'total_products_found': len(all_price_list),
                'PriceList': all_price_list,
            },
            pagination,
        )

        # Offload large responses to SQLite via the size gate; small responses
        # fall through to the human-readable processing below.
        table_response = await convert_response_if_needed(
            ctx, raw_response, 'aws_pricing_get_products', service_code=service_code
        )

        # If table was created, return that, otherwise process the response for easier consumption
        if isinstance(table_response, dict) and 'data_stored' in table_response:
            return format_response('success', table_response)

        # Process the pricing data for easier consumption. max_items already bounds
        # what was fetched, so every fetched product is returned.
        display_limit = len(all_price_list)
        processed_products = []

        # Get context logger for consistent logging
        ctx_logger = get_context_logger(ctx, __name__)

        # Keep track of products that fail to parse
        failed_products = 0

        for i, product_json in enumerate(all_price_list):
            try:
                # Wrap the JSON parsing in a try-except block
                product = json.loads(product_json)

                # Process the product data
                processed_product = {
                    'sku': product.get('product', {}).get('sku'),
                    'productFamily': product.get('product', {}).get('productFamily'),
                    'attributes': product.get('product', {}).get('attributes', {}),
                }

                # Returned as given: Reserved prices are told apart by termAttributes
                # and tiered prices by beginRange/endRange.
                processed_product['terms'] = product.get('terms', {})
                processed_products.append(processed_product)

            except json.JSONDecodeError as e:
                # Log the error but continue processing other products
                failed_products += 1
                await ctx_logger.error(
                    f'Failed to parse product JSON at index {i}: {str(e)}. '
                    f'First 100 chars: {product_json[:100] if len(product_json) > 100 else product_json}'
                )

                # Add a placeholder for the failed product to maintain count
                processed_products.append(
                    {
                        'sku': f'parsing_failed_{i}',
                        'productFamily': 'Unknown',
                        'attributes': {'error': f'Failed to parse JSON: {str(e)}'},
                        'terms': {},
                    }
                )
            except Exception as e:
                # Handle any other exceptions
                failed_products += 1
                await ctx_logger.error(f'Error processing product at index {i}: {str(e)}')

                # Add a placeholder for the failed product
                processed_products.append(
                    {
                        'sku': f'processing_failed_{i}',
                        'productFamily': 'Unknown',
                        'attributes': {'error': f'Processing error: {str(e)}'},
                        'terms': {},
                    }
                )

        # Log summary of parsing failures if any
        if failed_products > 0:
            await ctx_logger.warning(
                f'Failed to parse {failed_products} out of {display_limit} products. '
                f'These products will have placeholder entries in the results.'
            )

        # Use shared format_response utility
        result: Dict[str, Any] = {
            'service_code': service_code,
            'filter_count': len(api_filters),
            'total_products_found': len(all_price_list),
            'products_returned': len(processed_products),
            'products': processed_products,
        }

        # Add parsing failure information if applicable
        if failed_products > 0:
            result['parsing_failures'] = failed_products
            result['parsing_success_rate'] = (
                f'{((display_limit - failed_products) / display_limit) * 100:.1f}%'
            )

        return format_response('success', with_pagination(result, pagination))

    except Exception as e:
        # Route through the shared handler so the response carries a top-level
        # error_type + operation (consistent structured error shape), while
        # keeping the legacy `data` payload for backward compatibility.
        classified = await handle_aws_error(
            ctx, e, 'get_pricing_from_api', AWS_PRICING_SERVICE_NAME
        )
        classified['data'] = {
            'message': f'Pricing API request failed: {str(e)}',
            'service_code': service_code,
            'note': 'AWS service codes typically follow patterns like "AmazonS3", "AmazonEC2", "AmazonES" (for OpenSearch), etc.',
        }
        return classified
