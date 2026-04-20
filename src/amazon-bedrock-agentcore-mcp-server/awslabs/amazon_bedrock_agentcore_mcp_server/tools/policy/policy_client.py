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

"""Cached boto3 client wrapper for AgentCore Policy APIs.

AgentCore Policy APIs (policy engines, policies, policy generation) all
live on the control plane (bedrock-agentcore-control). A single cached
client is shared across all Policy tool groups.
"""

import boto3
from awslabs.amazon_bedrock_agentcore_mcp_server.utils.user_agent import (
    build_user_agent,
)
from botocore.config import Config
from loguru import logger
from os import getenv
from typing import Any


MCP_USER_AGENT = build_user_agent('policy')

_policy_clients: dict[str, Any] = {}


def get_policy_client(region_name: str | None = None) -> Any:
    """Get a cached boto3 client for Policy control plane operations.

    Used by all Policy tool groups — policy engines, policies, and
    policy generation. All operations go through the
    bedrock-agentcore-control service.

    Args:
        region_name: AWS region. Defaults to AWS_REGION env var or us-east-1.

    Returns:
        Cached boto3 client for bedrock-agentcore-control.
    """
    region = region_name or getenv('AWS_REGION') or 'us-east-1'

    if region in _policy_clients:
        return _policy_clients[region]

    session = boto3.Session(region_name=region)
    client = session.client(
        'bedrock-agentcore-control',
        config=Config(user_agent_extra=MCP_USER_AGENT),
    )
    _policy_clients[region] = client

    logger.info(f'Created bedrock-agentcore-control client for region={region}')
    return client
