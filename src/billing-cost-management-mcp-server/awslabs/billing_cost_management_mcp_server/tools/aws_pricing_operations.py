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
import math
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

        data: Dict[str, Any] = {
            'service_code': service_code,
            'attribute_name': attribute_name,
            'values': values,
            'message': f'Successfully retrieved {len(values)} values for attribute {attribute_name} of service {service_code}',
        }
        # The API returns no values, not an error, for an attribute the service does not have.
        if not values and pagination['complete_dataset'] and not next_token:
            data['hint'] = (
                f'{service_code} has no values for {attribute_name!r}. The Price List API '
                'returns an empty list, not an error, when the attribute is not one of the '
                "service's attributes: check the name with get_service_attributes."
            )

        # Use shared format_response utility
        return format_response('success', with_pagination(data, pagination))

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


# Console names whose Price List service codes are easy to guess wrong.
SERVICE_CODE_EXAMPLES = {
    'OpenSearch': 'AmazonES',
    'Lambda': 'AWSLambda',
    'DynamoDB': 'AmazonDynamoDB',
    'Bedrock': 'AmazonBedrock',
}

# GetProducts Filter.Type values. TERM_MATCH and EQUALS are the same exact match, CONTAINS
# matches a substring, and ANY_OF and NONE_OF split Value on commas.
FILTER_TYPES = ('TERM_MATCH', 'EQUALS', 'CONTAINS', 'ANY_OF', 'NONE_OF')
_LIST_FILTER_TYPES = ('ANY_OF', 'NONE_OF')


def _filter_text(field: str, value: Any) -> str:
    """One filter value as the API takes it: a string, or a number as its text ('2', not '2.0')."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError(
            f'Filter {field!r}: each value must be a string or a number, not {json.dumps(value)}.'
        )
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f'Filter {field!r}: {value} is not a value the API can match.')
        if value.is_integer():
            return str(int(value))
    text = str(value)
    if not text.strip():
        raise ValueError(f'Filter {field!r}: the value is blank.')
    return text


def _filter_value(field: str, value: Any, filter_type: str) -> str:
    """A filter's Value: a list is comma-joined, which only ANY_OF and NONE_OF accept."""
    if not isinstance(value, list):
        if isinstance(value, (dict, type(None))):
            raise ValueError(
                f'Filter {field!r}: the value must be a string, a number or a list of them, '
                f'not {json.dumps(value)}.'
            )
        text = _filter_text(field, value)
        if filter_type in _LIST_FILTER_TYPES and not any(v.strip() for v in text.split(',')):
            raise ValueError(f'Filter {field!r}: {filter_type} needs at least one value.')
        return text
    if filter_type not in _LIST_FILTER_TYPES:
        raise ValueError(
            f'Filter {field!r}: a list of values needs Type ANY_OF or NONE_OF, not {filter_type}.'
        )
    if not value:
        raise ValueError(f'Filter {field!r}: the list of values is empty.')
    values = [_filter_text(field, item) for item in value]
    for item in values:
        if ',' in item:
            raise ValueError(
                f'Filter {field!r}: {item!r} contains a comma, which {filter_type} reads as a '
                'separator. Match that value on its own with TERM_MATCH, EQUALS or CONTAINS.'
            )
    return ','.join(values)


def _build_filters(parsed: Any) -> list:
    """The GetProducts Filters for the parsed filters argument.

    An object maps each attribute to a value: a string or number is a TERM_MATCH, a list an
    ANY_OF. A list is the API's own [{Field, Type, Value}] shape, for every filter type.
    """
    filters = []
    if isinstance(parsed, dict):
        for field, value in parsed.items():
            if value is None:
                continue
            if not field.strip():
                raise ValueError(f'Filter field names must be attribute names, not {field!r}.')
            filter_type = 'ANY_OF' if isinstance(value, list) else 'TERM_MATCH'
            filters.append(
                {
                    'Field': field,
                    'Type': filter_type,
                    'Value': _filter_value(field, value, filter_type),
                }
            )
        return filters
    if not isinstance(parsed, list):
        raise ValueError(
            'filters must be a JSON object such as {"instanceType": "m5.large"} or a JSON list '
            'such as [{"Field": "instanceType", "Type": "ANY_OF", "Value": "m5.large,m5.xlarge"}].'
        )
    for entry in parsed:
        if not isinstance(entry, dict) or set(entry) != {'Field', 'Type', 'Value'}:
            raise ValueError(
                'Each filter in a list must be an object with exactly the keys Field, Type and '
                f'Value, not {json.dumps(entry)}.'
            )
        field, filter_type = entry['Field'], entry['Type']
        if not isinstance(field, str) or not field.strip():
            raise ValueError(f'Filter Field must be an attribute name, not {json.dumps(field)}.')
        if filter_type not in FILTER_TYPES:
            raise ValueError(
                f'Filter {field!r}: Type must be one of {", ".join(FILTER_TYPES)}, '
                f'not {json.dumps(filter_type)}.'
            )
        filters.append(
            {
                'Field': field,
                'Type': filter_type,
                'Value': _filter_value(field, entry['Value'], filter_type),
            }
        )
    return filters


# Past this many names the hint points at varying_attributes instead of listing them.
_HINT_MAX_ATTRIBUTES = 10

# An offloaded response is not parsed whole; its guidance looks at this many products.
_GUIDANCE_SAMPLE = 1000


def _decode_products(price_list: list) -> list:
    """Parse each PriceList entry once: the product dict, or the exception that parsing raised."""
    decoded: list = []
    for product_json in price_list:
        try:
            decoded.append(json.loads(product_json))
        except Exception as e:
            decoded.append(e)
    return decoded


def _many_products_guidance(products: list, total: Optional[int] = None) -> Dict[str, Any]:
    """Name the attributes that tell several products apart, so one is not quoted as the price.

    Takes _decode_products output: every product, or the first of ``total`` products. Returns
    {} for one product or fewer. Entries without a product.attributes dict are skipped.
    """
    total = len(products) if total is None else total
    if total < 2:
        return {}
    values: Dict[str, set] = {}
    seen: Dict[str, int] = {}
    parsed = 0
    for product in products:
        try:
            attributes = product['product']['attributes']
        except (TypeError, KeyError):
            continue
        if not isinstance(attributes, dict):
            continue
        parsed += 1
        for name, value in attributes.items():
            values.setdefault(name, set()).add(repr(value))
            seen[name] = seen.get(name, 0) + 1
    # An attribute missing from some products also tells them apart.
    varying = sorted(n for n in values if len(values[n]) > 1 or seen[n] < parsed)
    they = f'In the first {len(products)}, they' if len(products) < total else 'They'
    if not varying:
        # Nothing to filter on: the products differ only in their terms, or did not parse.
        if parsed < max(len(products), 2):
            same = ''  # Too few parsed products to say anything about their attributes.
        elif len(products) < total:
            same = f' The first {parsed} have the same attributes; query the rest.'
        else:
            same = ' They have the same attributes.'
        return {
            'varying_attributes': varying,
            'hint': (
                f'This response has {total} products, each priced separately.{same} '
                'Compare their terms; do not quote the first product or an average.'
            ),
        }
    if len(varying) > _HINT_MAX_ATTRIBUTES:
        differ = f' {they} differ in {len(varying)} attributes (see varying_attributes).'
    else:
        differ = f' {they} differ in: {", ".join(varying)}.'
    return {
        'varying_attributes': varying,
        'hint': (
            f'This response has {total} products, each priced separately.{differ} '
            'To price one configuration, add filters for these attributes or pick the product '
            'whose attributes match; do not quote the first product or an average.'
        ),
    }


def _filters_matched_nothing(
    service_code: str, api_filters: list, service_known: Optional[bool]
) -> Dict[str, Any]:
    """The no_results response for filters that matched nothing.

    service_known is True when the service code returns products without filters, None when
    that check failed.
    """
    if service_known:
        cause = 'The service code is valid.'
    else:
        cause = 'Either the service code or a filter is wrong (checking the service code failed).'
    message = (
        f'No {service_code} products matched the filters {json.dumps(api_filters)}. {cause} '
        'The Price List API returns no products, not an error, when a field is not one of the '
        "service's attributes, a value is not one of its values, or no product has this "
        'combination of values (for example, an instance type not offered in that Region). '
        'Check fields with get_service_attributes and values with get_attribute_values, and '
        'drop filters one at a time to find the one that excludes everything.'
    )
    if any(f['Field'].lower() == 'location' for f in api_filters):
        message += (
            ' "location" takes the Price List location name (for example "US East (N. Virginia)"'
            ' or "EU (Ireland)"), not a region code; services with a "regionCode" attribute take'
            ' codes such as "us-east-1" in regionCode.'
        )
    exact_with_comma = [
        f for f in api_filters if f['Type'] in ('TERM_MATCH', 'EQUALS') and ',' in f['Value']
    ]
    if exact_with_comma:
        example = exact_with_comma[0]
        values = [v.strip() for v in example['Value'].split(',')]
        message += (
            f' A {example["Type"]} value with commas matches that whole string, not each part;'
            f' to match any of them, pass a list: {json.dumps({example["Field"]: values})}.'
        )
    data: Dict[str, Any] = {'message': message, 'filters': api_filters}
    if service_known is None:
        data['examples'] = dict(SERVICE_CODE_EXAMPLES)
    return {
        **format_response('error', data),
        'service': AWS_PRICING_SERVICE_NAME,
        'operation': 'get_pricing_from_api',
        'error_type': 'no_results',
        'message': message,
    }


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
            parsed_filters = parse_json(filters, 'filters')
            # An empty object or list sends no filter; any other JSON value is checked, so '0'
            # or 'false' is refused rather than fetching the whole service unfiltered.
            if parsed_filters is not None and parsed_filters != {} and parsed_filters != []:
                api_filters = _build_filters(parsed_filters)
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
            # An unknown filter field or value matches nothing without an error, just like an
            # unknown service code. One unfiltered product tells the two apart.
            if api_filters:
                try:
                    service_known: Optional[bool] = bool(
                        pricing_client.get_products(ServiceCode=service_code, MaxResults=1).get(
                            'PriceList'
                        )
                    )
                except Exception as e:
                    # The check only sharpens the message; it must not turn an empty result
                    # into an API error.
                    # Log the class only: AWS messages can repeat filter values.
                    await get_context_logger(ctx, __name__).warning(
                        f'Unfiltered GetProducts check failed: {type(e).__name__}'
                    )
                    service_known = None
                if service_known is not False:
                    return _filters_matched_nothing(service_code, api_filters, service_known)
            message = f'The service code "{service_code}" did not return any pricing data. AWS service codes typically follow patterns like "AmazonS3", "AmazonEC2", "AmazonES", etc. Please check the exact service code and try again.'
            return {
                **format_response(
                    'error', {'message': message, 'examples': dict(SERVICE_CODE_EXAMPLES)}
                ),
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
            sample = _decode_products(all_price_list[:_GUIDANCE_SAMPLE])
            guidance = _many_products_guidance(sample, total=len(all_price_list))
            return format_response('success', {**table_response, **guidance})

        # Small enough to return inline: parse every product once, for guidance and display.
        decoded_products = _decode_products(all_price_list)
        guidance = _many_products_guidance(decoded_products)

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
                # Parsed once above; re-raise a parse failure into the handlers below.
                product = decoded_products[i]
                if isinstance(product, Exception):
                    raise product

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
            **guidance,
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
