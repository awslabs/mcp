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

"""In-memory cache for AWS HealthOmics pricing data."""

import json
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_aws_session
from loguru import logger
from typing import Optional


class PricingCache:
    """In-memory cache for AWS HealthOmics pricing data.

    This class manages AWS Pricing API interactions with in-memory caching
    to reduce API calls for repeated analyses. The cache uses the format
    `{resource_type}:{region}` as the key.

    Attributes:
        SIZE_TO_CPUS: Mapping of instance size to vCPU count
        FAMILY_MEMORY_RATIO: Mapping of instance family to GiB per vCPU
    """

    _cache: dict[str, float] = {}
    _pricing_client = None

    # Instance type specifications
    SIZE_TO_CPUS: dict[str, int] = {
        'large': 2,
        'xlarge': 4,
        '2xlarge': 8,
        '4xlarge': 16,
        '8xlarge': 32,
        '12xlarge': 48,
        '16xlarge': 64,
        '24xlarge': 96,
        '32xlarge': 128,
        '48xlarge': 192,
    }

    FAMILY_MEMORY_RATIO: dict[str, int] = {
        'c': 2,  # 2 GiB per vCPU (compute optimized)
        'm': 4,  # 4 GiB per vCPU (general purpose)
        'r': 8,  # 8 GiB per vCPU (memory optimized)
        'g4dn': 4,  # GPU families
        'g5': 4,
        'g6': 4,
        'g6e': 4,
    }

    # Region name mapping for AWS Pricing API
    REGION_NAME_MAP: dict[str, str] = {
        'us-east-1': 'US East (N. Virginia)',
        'us-east-2': 'US East (Ohio)',
        'us-west-1': 'US West (N. California)',
        'us-west-2': 'US West (Oregon)',
        'eu-west-1': 'EU (Ireland)',
        'eu-west-2': 'EU (London)',
        'eu-central-1': 'EU (Frankfurt)',
        'ap-southeast-1': 'Asia Pacific (Singapore)',
        'ap-southeast-2': 'Asia Pacific (Sydney)',
        'ap-northeast-1': 'Asia Pacific (Tokyo)',
        'ap-northeast-2': 'Asia Pacific (Seoul)',
        'il-central-1': 'Israel (Tel Aviv)',
    }

    @classmethod
    def get_price(cls, resource_type: str, region: str) -> Optional[float]:
        """Get price per hour for a resource type in a region.

        First checks the in-memory cache, then fetches from AWS Pricing API
        if not cached.

        Args:
            resource_type: The resource type (e.g., instance type like "omics.m.xlarge"
                          or storage type like "Run Storage", "Dynamic Run Storage")
            region: AWS region (e.g., "us-east-1")

        Returns:
            Price per hour (or per GiB-hour for storage), or None if unavailable
        """
        cache_key = f'{resource_type}:{region}'

        if cache_key in cls._cache:
            logger.debug(f'Cache hit for {cache_key}')
            return cls._cache[cache_key]

        logger.debug(f'Cache miss for {cache_key}, fetching from API')
        price = cls._fetch_price_from_api(resource_type, region)
        if price is not None:
            cls._cache[cache_key] = price
        return price

    @classmethod
    def get_price_with_error(
        cls, resource_type: str, region: str
    ) -> tuple[Optional[float], Optional[str]]:
        """Get price per hour for a resource type with error message support.

        This method provides the same functionality as get_price() but also
        returns an error message when pricing is unavailable, allowing callers
        to propagate error information to clients.

        Args:
            resource_type: The resource type (e.g., instance type like "omics.m.xlarge"
                          or storage type like "Run Storage", "Dynamic Run Storage")
            region: AWS region (e.g., "us-east-1")

        Returns:
            Tuple of (price, error_message):
            - (float, None) if price was retrieved successfully
            - (None, str) if pricing is unavailable with descriptive error message
        """
        try:
            price = cls.get_price(resource_type, region)
            if price is None:
                error_msg = f'Unable to retrieve pricing for {resource_type} in {region}'
                logger.warning(error_msg)
                return None, error_msg
            return price, None
        except Exception as e:
            error_msg = f'Pricing API error for {resource_type} in {region}: {str(e)}'
            logger.warning(error_msg)
            return None, error_msg

    @classmethod
    def _get_pricing_client(cls):
        """Get or create the AWS Pricing API client.

        The Pricing API is only available in us-east-1 and ap-south-1.

        Returns:
            boto3 pricing client
        """
        if cls._pricing_client is None:
            session = get_aws_session()
            # Pricing API is only available in us-east-1
            cls._pricing_client = session.client('pricing', region_name='us-east-1')
        return cls._pricing_client

    @classmethod
    def _fetch_price_from_api(cls, resource_type: str, region: str) -> Optional[float]:
        """Fetch price from AWS Pricing API.

        Args:
            resource_type: The resource type (instance type or storage type)
            region: AWS region

        Returns:
            Price per hour (or per GiB-hour for storage), or None if unavailable
        """
        try:
            client = cls._get_pricing_client()
            region_name = cls.REGION_NAME_MAP.get(region)

            if not region_name:
                logger.warning(f'Unknown region {region}, cannot fetch pricing')
                return None

            # Build filters based on resource type
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': region_name},
            ]

            # Determine if this is an instance type or storage type
            if resource_type.startswith('omics.'):
                # Instance type pricing - use resourceType attribute
                filters.append(
                    {'Type': 'TERM_MATCH', 'Field': 'resourceType', 'Value': resource_type}
                )
            else:
                # Storage type pricing (e.g., "Run Storage", "Dynamic Run Storage")
                # Use resourceType attribute for storage as well
                filters.append(
                    {'Type': 'TERM_MATCH', 'Field': 'resourceType', 'Value': resource_type}
                )

            response = client.get_products(
                ServiceCode='AmazonOmics',
                Filters=filters,
                MaxResults=1,
            )

            if not response.get('PriceList'):
                logger.warning(f'No pricing found for {resource_type} in {region}')
                return None

            # Parse the price from the response
            price_item = json.loads(response['PriceList'][0])
            terms = price_item.get('terms', {}).get('OnDemand', {})

            for term_key in terms:
                price_dimensions = terms[term_key].get('priceDimensions', {})
                for dim_key in price_dimensions:
                    price_per_unit = price_dimensions[dim_key].get('pricePerUnit', {})
                    usd_price = price_per_unit.get('USD')
                    if usd_price:
                        return float(usd_price)

            logger.warning(f'Could not parse price for {resource_type} in {region}')
            return None

        except Exception as e:
            logger.warning(f'Pricing API error for {resource_type} in {region}: {e}')
            return None

    @classmethod
    def get_instance_specs(cls, instance_type: str) -> tuple[int, float]:
        """Get CPU count and memory for an instance type.

        Parses the instance type string (e.g., "omics.m.xlarge") to determine
        the CPU count and memory based on the family and size.

        Args:
            instance_type: HealthOmics instance type (e.g., "omics.m.xlarge")

        Returns:
            Tuple of (cpu_count, memory_gib). Returns (0, 0.0) if the instance
            type cannot be parsed.
        """
        try:
            # Remove "omics." prefix if present
            normalized = instance_type.replace('omics.', '')

            # Split into family and size
            parts = normalized.split('.')
            if len(parts) != 2:
                logger.warning(f'Invalid instance type format: {instance_type}')
                return (0, 0.0)

            family, size = parts[0], parts[1]

            # Get CPU count from size
            cpus = cls.SIZE_TO_CPUS.get(size, 0)
            if cpus == 0:
                logger.warning(f'Unknown instance size: {size}')
                return (0, 0.0)

            # Get memory ratio from family
            memory_ratio = cls.FAMILY_MEMORY_RATIO.get(family, 4)  # Default to 4 GiB/vCPU
            memory = float(cpus * memory_ratio)

            return (cpus, memory)

        except Exception as e:
            logger.warning(f'Error parsing instance type {instance_type}: {e}')
            return (0, 0.0)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the pricing cache.

        Useful for testing or when pricing data needs to be refreshed.
        """
        cls._cache.clear()
        logger.debug('Pricing cache cleared')

    @classmethod
    def get_cache_size(cls) -> int:
        """Get the number of entries in the cache.

        Returns:
            Number of cached pricing entries
        """
        return len(cls._cache)
