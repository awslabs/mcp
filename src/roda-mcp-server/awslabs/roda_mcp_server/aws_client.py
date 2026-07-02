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

"""AWS client utilities for the RODA MCP Server."""

import boto3
from awslabs.roda_mcp_server import __version__
from botocore import UNSIGNED
from botocore.config import Config
from loguru import logger
from typing import Any


def get_s3_client(region: str = 'us-east-1') -> Any:
    """Get an anonymous S3 client for public dataset access.

    Uses UNSIGNED signature (no credentials required).
    Only works for publicly accessible buckets.

    Args:
        region: AWS region for the S3 endpoint (default: us-east-1)

    Returns:
        Configured S3 client with anonymous access

    Raises:
        Exception: If client creation fails
    """
    try:
        config = Config(
            signature_version=UNSIGNED,
            s3={'use_ssl': True},
            user_agent_extra=f'md/awslabs#mcp#roda-mcp-server#{__version__}',
        )
        logger.debug(f'Creating anonymous S3 client for region: {region}')
        return boto3.client('s3', config=config, region_name=region, verify=True)

    except Exception as e:
        logger.error(f'Failed to create S3 client: {e}')
        raise
