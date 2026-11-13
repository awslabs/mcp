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

"""Cached boto3 client for the AgentCore Web Search API (InvokeWebSearch).

Web search is a data plane operation on the bedrock-agentcore service.
Requests are signed with SigV4 using the standard boto3 credential chain.
"""

import boto3
from awslabs.amazon_bedrock_agentcore_mcp_server.utils.user_agent import (
    build_user_agent,
)
from botocore.config import Config
from functools import cache
from loguru import logger
from os import getenv
from typing import Any


@cache
def get_web_search_client() -> Any:
    """Get the cached boto3 bedrock-agentcore client for web search.

    The region comes from the AWS_REGION env var, or us-east-1.

    Returns:
        Cached boto3 client for bedrock-agentcore.
    """
    region = getenv('AWS_REGION') or 'us-east-1'
    client = boto3.Session(region_name=region).client(
        'bedrock-agentcore',
        config=Config(user_agent_extra=build_user_agent('web-search')),
    )
    logger.info(f'Created bedrock-agentcore web search client for region={region}')
    return client
