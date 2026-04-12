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

"""Cached boto3 client factories for AgentCore Runtime.

Control plane operations (CRUD on runtimes and endpoints) use
``bedrock-agentcore-control``.  Data plane operations (invoke,
stop session) use ``bedrock-agentcore``.
"""

import boto3
from awslabs.amazon_bedrock_agentcore_mcp_server.utils.user_agent import (
    build_user_agent,
)
from botocore.config import Config
from loguru import logger
from os import getenv
from typing import Any, Dict


_control_clients: Dict[str, Any] = {}
_data_clients: Dict[str, Any] = {}

MCP_CONTROL_USER_AGENT = build_user_agent('runtime', 'control')
MCP_DATA_USER_AGENT = build_user_agent('runtime')


def get_control_client(region_name: str | None = None) -> Any:
    """Get or create a cached control-plane client.

    Args:
        region_name: AWS region. Defaults to AWS_REGION env var or us-east-1.

    Returns:
        Cached ``bedrock-agentcore-control`` client instance.
    """
    region = region_name or getenv('AWS_REGION') or 'us-east-1'
    if region in _control_clients:
        return _control_clients[region]
    session = boto3.Session(region_name=region)
    client = session.client(
        'bedrock-agentcore-control',
        config=Config(user_agent_extra=MCP_CONTROL_USER_AGENT),
    )
    _control_clients[region] = client
    logger.info(f'Created bedrock-agentcore-control client for region={region}')
    return client


def get_data_client(region_name: str | None = None) -> Any:
    """Get or create a cached data-plane client.

    Args:
        region_name: AWS region. Defaults to AWS_REGION env var or us-east-1.

    Returns:
        Cached ``bedrock-agentcore`` client instance.
    """
    region = region_name or getenv('AWS_REGION') or 'us-east-1'
    if region in _data_clients:
        return _data_clients[region]
    session = boto3.Session(region_name=region)
    client = session.client(
        'bedrock-agentcore',
        config=Config(user_agent_extra=MCP_DATA_USER_AGENT),
    )
    _data_clients[region] = client
    logger.info(f'Created bedrock-agentcore client for region={region}')
    return client
