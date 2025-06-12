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

"""Describe serverless cache operations."""

from ...common.connection import ElastiCacheConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from typing import Dict, Optional


@mcp.tool(name='describe-serverless-caches')
@handle_exceptions
async def describe_serverless_caches(
    serverless_cache_name: Optional[str] = None,
    max_items: Optional[int] = None,
    starting_token: Optional[str] = None,
    page_size: Optional[int] = None,
) -> Dict:
    """Describe Amazon ElastiCache serverless caches in your AWS account.

    This tool retrieves detailed information about serverless caches including:
    - Cache configuration
    - Cache endpoints
    - Cache status
    - Cache size
    - Cache connections

    Parameters:
        serverless_cache_name (Optional[str]): Name of the serverless cache to describe. If not provided, describes all caches.
        max_items (Optional[int]): Maximum number of results to return.
        starting_token (Optional[str]): Token to start the list from a specific page.
        page_size (Optional[int]): Number of records to include in each page.

    Returns:
        Dict containing information about the serverless cache(s).
    """
    # Get ElastiCache client
    elasticache_client = ElastiCacheConnectionManager.get_connection()

    if serverless_cache_name:
        # Get specific cache details
        response = elasticache_client.describe_serverless_caches(
            ServerlessCacheName=serverless_cache_name
        )
        return response
    else:
        # List all caches with optional pagination
        kwargs = {}
        if max_items:
            kwargs['MaxItems'] = max_items
        if starting_token:
            kwargs['StartingToken'] = starting_token
        if page_size:
            kwargs['PageSize'] = page_size

        response = elasticache_client.describe_serverless_caches(**kwargs)
        return response
