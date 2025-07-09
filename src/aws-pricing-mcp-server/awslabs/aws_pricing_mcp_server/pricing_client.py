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

"""awslabs MCP AWS Pricing mcp server pricing client.

This module provides utilities for creating boto3 pricing clients.
"""

import boto3
import sys
from awslabs.aws_pricing_mcp_server import __version__, consts
from botocore.config import Config
from loguru import logger
from typing import Any, Optional


# Set up logging
logger.remove()
logger.add(sys.stderr, level=consts.LOG_LEVEL)


def get_pricing_region(requested_region: Optional[str] = None) -> str:
    """Determine the appropriate AWS Pricing API region.

    The AWS Pricing API is only available in specific regions:
    - Classic partition: us-east-1, eu-central-1, ap-southeast-1
    - China partition: cn-northwest-1

    This function maps the requested region to the nearest pricing endpoint
    based on region prefixes.

    Args:
        requested_region: The AWS region requested by the user (default: None)

    Returns:
        The appropriate pricing API region
    """
    # If no region specified, check environment variable
    if not requested_region:
        requested_region = consts.AWS_REGION

    # If the requested region is already a pricing region, use it directly
    all_pricing_regions = (
        consts.PRICING_API_REGIONS['classic'] + consts.PRICING_API_REGIONS['china']
    )
    if requested_region in all_pricing_regions:
        logger.debug(f'Using pricing region directly: {requested_region}')
        return requested_region

    # Map regions based on prefix to nearest pricing endpoint
    if requested_region.startswith('cn-'):
        # China regions
        pricing_region = 'cn-northwest-1'
    elif requested_region.startswith(('eu-', 'me-', 'af-')):
        # Europe, Middle East, and Africa regions
        pricing_region = 'eu-central-1'
    elif requested_region.startswith('ap-'):
        # Asia Pacific regions
        pricing_region = 'ap-southeast-1'
    else:
        # Default to US East (covers us-, ca-, sa- and any unknown regions)
        pricing_region = 'us-east-1'

    if pricing_region != requested_region:
        logger.info(
            f'Region {requested_region} does not have pricing API. Using {pricing_region} instead.'
        )

    return pricing_region


def create_pricing_client(profile: Optional[str] = None, region: Optional[str] = None) -> Any:
    """Create an AWS Pricing API client.

    Args:
        profile: AWS profile name to use (default: None, uses AWS_PROFILE or default profile)
        region: AWS region name (default: None, uses AWS_REGION env var or nearest pricing region)

    Returns:
        boto3 pricing client
    """
    session = boto3.Session(profile_name=profile if profile else consts.AWS_PROFILE)

    # Determine the appropriate pricing region
    pricing_region = get_pricing_region(region)

    config = Config(
        region_name=pricing_region,
        user_agent_extra=f'awslabs/mcp/{consts.MCP_SERVER_NAME}/{__version__}',
    )

    logger.debug(f'Creating pricing client for region: {pricing_region}')
    return session.client('pricing', config=config)
