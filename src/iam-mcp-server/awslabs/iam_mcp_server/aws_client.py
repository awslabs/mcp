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

"""AWS client utilities for the IAM MCP Server."""

import boto3
from awslabs.iam_mcp_server.context import Context
from botocore.config import Config
from loguru import logger
from typing import Any, Optional


def get_iam_client(region: Optional[str] = None) -> Any:
    """Get an IAM client with proper configuration.

    Args:
        region: Optional AWS region override

    Returns:
        Configured IAM client

    Raises:
        Exception: If client creation fails
    """
    try:
        # Use provided region, context region, or default
        client_region = region or Context.get_region()

        # Add user agent to identify this MCP server in AWS logs
        config = Config(user_agent_extra='awslabs-iam-mcp-server/1.0.0')

        if client_region:
            logger.debug(f'Creating IAM client for region: {client_region}')
            return boto3.client('iam', region_name=client_region, config=config)
        else:
            logger.debug('Creating IAM client with default region')
            return boto3.client('iam', config=config)

    except Exception as e:
        logger.error(f'Failed to create IAM client: {e}')
        raise Exception(f'Failed to create IAM client: {str(e)}')


def get_aws_client(service_name: str, region: Optional[str] = None) -> Any:
    """Get a generic AWS client for any service.

    Args:
        service_name: Name of the AWS service (e.g., 'iam', 's3', 'ec2')
        region: Optional AWS region override

    Returns:
        Configured AWS client

    Raises:
        Exception: If client creation fails
    """
    try:
        # Use provided region, context region, or default
        client_region = region or Context.get_region()

        # Add user agent to identify this MCP server in AWS logs
        config = Config(user_agent_extra='awslabs-iam-mcp-server/1.0.0')

        if client_region:
            logger.debug(f'Creating {service_name} client for region: {client_region}')
            return boto3.client(service_name, region_name=client_region, config=config)
        else:
            logger.debug(f'Creating {service_name} client with default region')
            return boto3.client(service_name, config=config)

    except Exception as e:
        logger.error(f'Failed to create {service_name} client: {e}')
        raise Exception(f'Failed to create {service_name} client: {str(e)}')
