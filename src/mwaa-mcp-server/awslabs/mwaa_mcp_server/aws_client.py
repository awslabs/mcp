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

"""AWS client factory for the MWAA MCP Server."""

from awslabs.mwaa_mcp_server import MCP_SERVER_VERSION
from awslabs.mwaa_mcp_server.consts import DEFAULT_REGION, ENV_AWS_PROFILE, ENV_AWS_REGION
from boto3 import Session
from botocore.config import Config
from os import getenv


def get_mwaa_client(
    region_name: str | None = None,
    profile_name: str | None = None,
):
    """Create an MWAA boto3 client with custom user-agent.

    Args:
        region_name: AWS region. Defaults to AWS_REGION env var or us-east-1 if not set.
        profile_name: AWS CLI profile name. Falls back to AWS_PROFILE env var if not specified,
            or uses default AWS credential chain.

    Returns:
        boto3 MWAA client for the specified region.
    """
    if profile_name is None:
        profile_name = getenv(ENV_AWS_PROFILE, None)

    config = Config(
        user_agent_extra=f'awslabs/mcp/mwaa-mcp-server/{MCP_SERVER_VERSION}',
        read_timeout=30,
        connect_timeout=10,
    )

    if profile_name:
        session = Session(profile_name=profile_name)
    else:
        session = Session()

    region = region_name or getenv(ENV_AWS_REGION, None) or session.region_name or DEFAULT_REGION

    return session.client('mwaa', region_name=region, config=config)
