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

"""Pricing transformation functionality for the aws-pricing-mcp-server."""

import json
import logging
from .models import OutputOptions
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


def _is_free_product(pricing_item: Dict[str, Any]) -> bool:
    """Check if product has only $0.00 OnDemand pricing across all currencies.

    Args:
        pricing_item: Parsed pricing item dictionary

    Returns:
        True if all OnDemand pricing is $0.00 in all currencies, False otherwise
    """
    ondemand_terms = pricing_item.get('terms', {}).get('OnDemand', {})

    if not ondemand_terms:
        return False  # No OnDemand pricing available

    # Check all OnDemand pricing dimensions
    for _, offer_data in ondemand_terms.items():
        price_dimensions = offer_data.get('priceDimensions', {})

        for _, price_dim in price_dimensions.items():
            price_per_unit = price_dim.get('pricePerUnit', {})

            for _, price_value in price_per_unit.items():
                try:
                    if float(price_value) > 0:
                        return False  # Found non-zero price in any currency
                except (ValueError, TypeError):
                    # Invalid price format (e.g., "N/A", "Variable"), assume not free
                    return False

    return True


def transform_pricing_data(
    pricing_json_list: List[str], output_options: Optional[OutputOptions]
) -> List[Dict[str, Any]]:
    """Filter and optimize AWS pricing data for reduced response size.

    Args:
        pricing_json_list: List of JSON strings from AWS Pricing API
        output_options: Optional filtering options for pricing terms and product attributes

    Returns:
        List of filtered pricing records as dictionaries

    Raises:
        ValueError: If JSON parsing fails for any record
    """
    if not pricing_json_list:
        return []

    # Parse all JSON strings upfront with error handling
    parsed_data = []
    for i, json_str in enumerate(pricing_json_list):
        try:
            parsed_item = json.loads(json_str)
            # Remove redundant serviceCode field (optimization)
            parsed_item.pop('serviceCode', None)
            parsed_data.append(parsed_item)
        except json.JSONDecodeError as e:
            raise ValueError(f'Invalid JSON format in pricing data at index {i}: {e}')

    # Return early if no filtering is needed
    if output_options is None:
        return parsed_data

    result = []
    for item in parsed_data:
        # Filter out free products first (before removing OnDemand terms)
        if output_options.exclude_free_products and _is_free_product(item):
            continue  # Skip this item

        # Start with original item, modify only what's needed
        filtered_item = item

        # Apply pricing terms filtering
        if output_options.pricing_terms is not None and 'terms' in item:
            filtered_terms = {
                term_type: item['terms'][term_type]
                for term_type in output_options.pricing_terms
                if term_type in item['terms']
            }
            filtered_item = {**item, 'terms': filtered_terms}

        # Apply product attributes filtering
        if (
            output_options.product_attributes is not None
            and 'product' in filtered_item
            and 'attributes' in filtered_item['product']
        ):
            original_attributes = filtered_item['product']['attributes']
            filtered_attributes = {
                attr_name: original_attributes[attr_name]
                for attr_name in output_options.product_attributes
                if attr_name in original_attributes
            }
            filtered_item = {
                **filtered_item,
                'product': {**filtered_item['product'], 'attributes': filtered_attributes},
            }

        result.append(filtered_item)

    return result
