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

"""Browser discovery and management tools."""

from __future__ import annotations

from awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client import (
    get_control_plane_client,
    handle_aws_errors,
)
from loguru import logger


@handle_aws_errors('list browsers')
def list_browsers(browser_type: str | None = None, max_results: int = 10) -> dict:
    """List available browser tools in the account.

    Discovers browser tool IDs for use with session tools. Types:
    - SYSTEM: AWS-managed browsers (e.g., "aws.browser.v1")
    - CUSTOM: User-created browsers with VPC/network configurations

    Args:
        browser_type: Filter by type ("SYSTEM" or "CUSTOM"). None returns all.
        max_results: Maximum browsers to return (default: 10).

    Returns:
        dict with browsers list and next_token for pagination.
    """
    logger.info(f'Listing browsers: type={browser_type}')
    client = get_control_plane_client()

    params: dict = {'maxResults': max_results}
    if browser_type is not None:
        params['type'] = browser_type

    response = client.list_browsers(**params)

    browsers = [
        {
            'browser_id': b.get('browserId'),
            'name': b.get('name'),
            'status': b.get('status'),
            'type': b.get('type'),
        }
        for b in response.get('browsers', [])
    ]

    return {'browsers': browsers, 'next_token': response.get('nextToken')}


@handle_aws_errors('get browser')
def get_browser(browser_id: str) -> dict:
    """Get detailed information about a specific browser tool.

    Returns network configuration, status, and metadata. Useful for inspecting
    VPC-bound custom browsers before creating sessions.

    Args:
        browser_id: Unique identifier (e.g., "aws.browser.v1" or a custom ID).

    Returns:
        dict with browser_id, name, description, status, type, network_configuration, created_at.
    """
    logger.info(f'Getting browser details: {browser_id}')
    client = get_control_plane_client()

    response = client.get_browser(browserId=browser_id)

    return {
        'browser_id': response.get('browserId'),
        'name': response.get('name'),
        'description': response.get('description'),
        'status': response.get('status'),
        'type': response.get('type'),
        'network_configuration': response.get('networkConfiguration'),
        'created_at': response.get('createdAt'),
    }
