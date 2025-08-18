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
from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    get_pricing_region,
    parse_json,
)
from ..utilities.logging_utils import get_context_logger
from ..utilities.sql_utils import convert_api_response_to_table
from fastmcp import Context
from typing import Any, Dict, Optional


async def get_service_codes(ctx: Context, max_results: Optional[int] = None) -> Dict[str, Any]:
    """Retrieve all available service codes from AWS Price List API.

    Uses shared utilities for client creation and response formatting.

    Args:
        ctx: MCP context
        max_results: Maximum number of results to return

    Returns:
        Dict containing service codes
    """
    try:
        await ctx.info('Retrieving AWS service codes from Price List API')

        # Create pricing client using shared utility
        pricing_client = create_aws_client('pricing', 'us-east-1')

        # Initialize collection variables
        service_codes = []
        next_token = None
        page_count = 0

        # Fetch all pages
        while True:
            page_count += 1

            # Prepare request parameters
            params: Dict[str, Any] = {}
            if next_token:
                params['NextToken'] = next_token
            if max_results:
                params['MaxResults'] = int(max_results)

            # Make API call
            await ctx.info(f'Fetching service codes page {page_count}')
            response = pricing_client.describe_services(**params)

            # Process results
            page_services = response.get('Services', [])
            for service in page_services:
                service_codes.append(service['ServiceCode'])

            await ctx.info(
                f'Retrieved {len(page_services)} services (total: {len(service_codes)})'
            )

            # Check for more pages
            next_token = response.get('NextToken')
            if not next_token:
                break

        # Sort for consistent output
        sorted_codes = sorted(service_codes)

        # Use shared format_response utility
        return format_response(
            'success',
            {
                'service_codes': sorted_codes,
                'total_count': len(sorted_codes),
                'message': f'Successfully retrieved {len(sorted_codes)} AWS service codes',
            },
        )

    except Exception as e:
        # Use standard error format
        return format_response('error', {'message': f'Error retrieving service codes: {str(e)}'})


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
        pricing_client = create_aws_client('pricing', 'us-east-1')

        # Make API call
        response = pricing_client.describe_services(ServiceCode=service_code)

        # Check if service exists
        if not response.get('Services'):
            return format_response(
                'error', {'message': f'No service found with code: {service_code}'}
            )

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
                'total_count': len(sorted_attributes),
                'message': f'Successfully retrieved {len(sorted_attributes)} attributes for {service_code}',
            },
        )

    except Exception as e:
        # Use standard error format
        return format_response(
            'error',
            {'message': f'Failed to retrieve attributes for service {service_code}: {str(e)}'},
        )


async def get_attribute_values(
    ctx: Context, service_code: str, attribute_name: str, max_results: Optional[int] = None
) -> Dict[str, Any]:
    """Retrieve all possible values for a specific attribute of an AWS service.

    Args:
        ctx: MCP context
        service_code: AWS service code
        attribute_name: Service attribute name
        max_results: Maximum number of results to return

    Returns:
        Dict containing attribute values
    """
    try:
        await ctx.info(
            f"Retrieving values for attribute '{attribute_name}' of service '{service_code}'"
        )

        # Create pricing client using shared utility
        pricing_client = create_aws_client('pricing', 'us-east-1')

        # Initialize collection variables
        values = []
        next_token = None
        page_count = 0

        # Fetch all pages
        while True:
            page_count += 1

            # Prepare request parameters
            params: Dict[str, Any] = {'ServiceCode': service_code, 'AttributeName': attribute_name}
            if next_token:
                params['NextToken'] = next_token
            if max_results is not None:
                params['MaxResults'] = max_results

            # Make API call
            await ctx.info(f'Fetching attribute values page {page_count}')
            response = pricing_client.get_attribute_values(**params)

            # Process results
            page_values = response.get('AttributeValues', [])
            for attr_value in page_values:
                if 'Value' in attr_value:
                    values.append(attr_value['Value'])

            await ctx.info(f'Retrieved {len(page_values)} values (total: {len(values)})')

            # Check for more pages
            next_token = response.get('NextToken')
            if not next_token:
                break

            # Stop if max_results is specified and we've reached it
            if max_results is not None and len(values) >= max_results:
                await ctx.info(f'Reached maximum results limit: {max_results}')
                break

        # Sort for consistent output
        sorted_values = sorted(values)

        # Use shared format_response utility
        return format_response(
            'success',
            {
                'service_code': service_code,
                'attribute_name': attribute_name,
                'values': sorted_values,
                'total_count': len(sorted_values),
                'message': f'Successfully retrieved {len(sorted_values)} values for attribute {attribute_name} of service {service_code}',
            },
        )

    except Exception as e:
        # Use standard error format
        return format_response(
            'error',
            {
                'message': f'Failed to retrieve values for attribute {attribute_name} of service {service_code}: {str(e)}'
            },
        )


async def get_pricing_from_api(
    ctx: Context,
    service_code: str,
    region: str,
    filters: Optional[str] = None,
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    """Get pricing information from AWS Price List API.

    Args:
        ctx: MCP context
        service_code: AWS service code
        region: AWS region
        filters: Optional filters as JSON string
        max_results: Maximum number of results to return

    Returns:
        Dict containing pricing data
    """
    try:
        await ctx.info(
            f"Retrieving pricing data for service '{service_code}' in region '{region}'"
        )

        # Determine correct pricing region
        pricing_region = get_pricing_region(region)
        await ctx.info(f'Using pricing API endpoint in region: {pricing_region}')

        # Create pricing client using shared utility
        pricing_client = create_aws_client('pricing', pricing_region)

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

        # Initialize collection variables
        all_price_list = []
        next_token = None
        page_count = 0

        # Fetch all pages
        while True:
            page_count += 1

            # Prepare request parameters
            params: Dict[str, Any] = {'ServiceCode': service_code, 'Filters': api_filters}
            if max_results:
                params['MaxResults'] = int(max_results)
            if next_token:
                params['NextToken'] = next_token

            # Make API call
            await ctx.info(f'Fetching pricing data page {page_count}')
            response = pricing_client.get_products(**params)

            # Process results
            price_list = response.get('PriceList', [])
            all_price_list.extend(price_list)

            await ctx.info(f'Retrieved {len(price_list)} products (total: {len(all_price_list)})')

            # Check for more pages
            next_token = response.get('NextToken')
            if not next_token:
                break

            # Stop if max_results is specified and we've reached it
            if max_results is not None and len(all_price_list) >= max_results:
                await ctx.info(f'Reached maximum results limit: {max_results}')
                break

        # Handle no results
        if not all_price_list:
            return format_response(
                'error',
                {
                    'message': f'The service code "{service_code}" did not return any pricing data. AWS service codes typically follow patterns like "AmazonS3", "AmazonEC2", "AmazonES", etc. Please check the exact service code and try again.',
                    'examples': {
                        'OpenSearch': 'AmazonES',
                        'Lambda': 'AWSLambda',
                        'DynamoDB': 'AmazonDynamoDB',
                        'Bedrock': 'AmazonBedrock',
                    },
                },
            )

        # Create response with raw data
        raw_response = {
            'service_code': service_code,
            'region': region,
            'filter_count': len(api_filters),
            'total_products_found': len(all_price_list),
            'PriceList': all_price_list,
        }

        # Convert large responses to SQL table
        table_response = await convert_api_response_to_table(
            ctx, raw_response, 'getPricing', service_code=service_code, region=region
        )

        # If table was created, return that, otherwise process the response for easier consumption
        if isinstance(table_response, dict) and 'data_stored' in table_response:
            return format_response('success', table_response)

        # Process the pricing data for easier consumption
        display_limit = min(
            len(all_price_list), max_results if max_results else 100
        )  # Limit to 100 by default
        processed_products = []

        # Get context logger for consistent logging
        ctx_logger = get_context_logger(ctx, __name__)

        # Keep track of products that fail to parse
        failed_products = 0

        for i, product_json in enumerate(all_price_list[:display_limit]):
            try:
                # Wrap the JSON parsing in a try-except block
                product = json.loads(product_json)

                # Process the product data
                processed_product = {
                    'sku': product.get('product', {}).get('sku'),
                    'productFamily': product.get('product', {}).get('productFamily'),
                    'attributes': product.get('product', {}).get('attributes', {}),
                }

                # Process terms in a more readable format
                terms = product.get('terms', {})
                processed_terms = {}

                for term_type, term_values in terms.items():
                    processed_terms[term_type] = []
                    for _, term_details in term_values.items():
                        price_dimensions = []

                        for _, dimension in term_details.get('priceDimensions', {}).items():
                            price_dimensions.append(
                                {
                                    'description': dimension.get('description'),
                                    'unit': dimension.get('unit'),
                                    'pricePerUnit': dimension.get('pricePerUnit'),
                                }
                            )

                        processed_terms[term_type].append(
                            {
                                'effectiveDate': term_details.get('effectiveDate'),
                                'priceDimensions': price_dimensions,
                            }
                        )

                processed_product['terms'] = processed_terms
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
        result = {
            'service_code': service_code,
            'region': region,
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

        return format_response('success', result)

    except Exception as e:
        # Use standard error format
        return format_response(
            'error',
            {
                'message': f'Pricing API request failed: {str(e)}',
                'service_code': service_code,
                'region': region,
                'note': 'AWS service codes typically follow patterns like "AmazonS3", "AmazonEC2", "AmazonES" (for OpenSearch), etc.',
            },
        )
