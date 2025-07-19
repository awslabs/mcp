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

"""Utility functions for AWS operations."""

import boto3
import logging
import os
from awslabs.aws_finops_mcp_server.consts import (
    DEFAULT_AWS_REGION,
    ENV_AWS_DEFAULT_REGION,
    ENV_AWS_REGION,
)
from typing import Any, Tuple


# Configure logging
logger = logging.getLogger(__name__)


def get_aws_region() -> Tuple[str, bool]:
    """Get AWS region from environment variables or use default.

    Returns:
        Tuple[str, bool]: A tuple containing:
            - The AWS region to use
            - A boolean indicating whether the region was explicitly set in environment variables
    """
    # Check if region is explicitly set in environment variables
    region_from_env = os.environ.get(ENV_AWS_DEFAULT_REGION) or os.environ.get(ENV_AWS_REGION)

    # If region is not set in environment, use default
    if region_from_env is None:
        return DEFAULT_AWS_REGION, False
    else:
        return region_from_env, True


def create_boto3_client(service_name: str, log_region: bool = True) -> Any:
    """Create a boto3 client with proper region handling.

    Args:
        service_name: The AWS service name to create a client for
        log_region: Whether to log the region being used

    Returns:
        boto3.client: A boto3 client for the specified service
    """
    region, is_region_from_env = get_aws_region()

    # Log warning if using default region
    if not is_region_from_env:
        logger.warning(
            f"No AWS region found in environment variables. Using hardcoded default '{DEFAULT_AWS_REGION}'. "
            f'Set {ENV_AWS_REGION} or {ENV_AWS_DEFAULT_REGION} environment variable to suppress this warning.'
        )

    if log_region:
        logger.info(f'Using region: {region}')

    return boto3.client(service_name, region_name=region)
