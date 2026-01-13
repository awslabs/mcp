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

"""AWS client utilities for CloudWatch MCP Server with multi-profile support."""

from awslabs.cloudwatch_mcp_server import MCP_SERVER_VERSION
from boto3 import Session
from botocore.config import Config
from os import getenv


def get_aws_client(
    service_name: str,
    region_name: str | None = None,
    profile_name: str | None = None,
):
    """AWS Client handler with multi-profile support.

    Args:
        service_name: AWS service name (e.g., 'logs', 'cloudwatch')
        region_name: AWS region. Defaults to AWS_REGION env var or us-east-1 if not set
        profile_name: AWS CLI profile name. Falls back to AWS_PROFILE env var if not specified,
            or uses default AWS credential chain

    Returns:
        boto3 client for the specified service
    """
    # Set profile from parameter or environment
    if profile_name is None:
        profile_name = getenv('AWS_PROFILE', None)

    # Configure user agent
    config = Config(user_agent_extra=f'awslabs/mcp/cloudwatch-mcp-server/{MCP_SERVER_VERSION}')

    # Create session with or without profile
    if profile_name:
        session = Session(profile_name=profile_name)
    else:
        session = Session()

    # Use provided region, or session's region, or fallback to us-east-1
    region = region_name or session.region_name or 'us-east-1'

    return session.client(service_name, region_name=region, config=config)
