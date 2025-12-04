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

"""Centralized AWS IoT SiteWise client creation utility."""

import boto3
from awslabs.aws_iot_sitewise_mcp_server import __version__
from botocore.config import Config


def create_sitewise_client(region: str = 'us-east-1'):
    """Create a standardized AWS IoT SiteWise client with proper user agent.

    Args:
        region: AWS region name (default: us-east-1)

    Returns:
        boto3 IoT SiteWise client instance
    """
    config = Config(user_agent_extra=f'awslabs/mcp/aws-iot-sitewise-mcp-server/{__version__}')

    return boto3.client('iotsitewise', region_name=region, config=config)


def create_iam_client(region: str = 'us-east-1'):
    """Create a standardized AWS IAM client with proper user agent.

    Args:
        region: AWS region name (default: us-east-1)

    Returns:
        boto3 IAM client instance
    """
    config = Config(user_agent_extra=f'awslabs/mcp/aws-iot-sitewise-mcp-server/{__version__}')

    return boto3.client('iam', region_name=region, config=config)


def create_twinmaker_client(region: str = 'us-east-1'):
    """Create a standardized AWS IoT TwinMaker client with proper user agent.

    Args:
        region: AWS region name (default: us-east-1)

    Returns:
        boto3 IoT TwinMaker client instance
    """
    config = Config(user_agent_extra=f'awslabs/mcp/aws-iot-sitewise-mcp-server/{__version__}')

    return boto3.client('iottwinmaker', region_name=region, config=config)
