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

"""AWS client utilities via bedrock-agentcore SDK."""

from bedrock_agentcore.tools import BrowserClient
from loguru import logger
from os import getenv


_browser_clients: dict[str, BrowserClient] = {}

MCP_INTEGRATION_SOURCE = 'awslabs-mcp-browser-server'


def get_browser_client(
    region_name: str | None = None,
) -> BrowserClient:
    """Get a cached BrowserClient for the specified region.

    Uses the bedrock-agentcore SDK to manage boto3 clients, endpoint
    resolution, and user-agent tagging. Credentials are resolved from
    the environment (AWS_PROFILE, AWS_ACCESS_KEY_ID, IAM role, etc.).

    Args:
        region_name: AWS region. Defaults to AWS_REGION env var or us-east-1.

    Returns:
        Cached BrowserClient instance.
    """
    region = region_name or getenv('AWS_REGION') or 'us-east-1'

    if region in _browser_clients:
        return _browser_clients[region]

    client = BrowserClient(region=region, integration_source=MCP_INTEGRATION_SOURCE)
    _browser_clients[region] = client

    logger.info(f'Created BrowserClient for region={region}')
    return client
