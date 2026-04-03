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

"""Create API Cache tool for AWS AppSync MCP Server."""

from awslabs.aws_appsync_mcp_server.decorators import write_operation
from awslabs.aws_appsync_mcp_server.operations.create_api_cache import create_api_cache_operation
from mcp.types import ToolAnnotations
from pydantic import Field
from typing import Annotated, Dict, Optional


def register_create_api_cache_tool(mcp):
    """Register the create_api_cache tool with the MCP server."""

    @mcp.tool(
        name='create_api_cache',
        description="""Creates a cache for the GraphQL API.

        This operation creates an API cache for the specified GraphQL API. Caching improves
        performance by storing frequently requested data and reducing the number of requests
        to data sources.
        """,
        annotations=ToolAnnotations(
            title='Create API Cache',
            readOnlyHint=False,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    @write_operation
    async def create_api_cache(
        api_id: Annotated[str, Field(description='The GraphQL API ID')],
        ttl: Annotated[
            int,
            Field(
                description='TTL in seconds for entries in the API cache. Valid values are 1-3600 seconds'
            ),
        ],
        api_caching_behavior: Annotated[
            str,
            Field(
                description='Caching behavior. Valid values: FULL_REQUEST_CACHING, PER_RESOLVER_CACHING'
            ),
        ],
        type: Annotated[
            str,
            Field(
                description='The cache instance type. Valid values: SMALL, MEDIUM, LARGE, XLARGE, LARGE_2X, LARGE_4X, LARGE_8X, LARGE_12X'
            ),
        ],
        transit_encryption_enabled: Annotated[
            Optional[bool], Field(description='Transit encryption flag when connecting to cache')
        ] = None,
        at_rest_encryption_enabled: Annotated[
            Optional[bool], Field(description='At-rest encryption flag for cache')
        ] = None,
        health_metrics_config: Annotated[
            Optional[str],
            Field(description='The health metrics configuration. Valid values: ENABLED, DISABLED'),
        ] = None,
    ) -> Dict:
        """Creates a cache for the GraphQL API.

        This operation creates an API cache for the specified GraphQL API. Caching improves
        performance by storing frequently requested data and reducing the number of requests
        to data sources.

        Args:
            api_id: The GraphQL API ID.
            ttl: TTL in seconds for entries in the API cache. Valid values are 1-3600 seconds.
            api_caching_behavior: Caching behavior. Valid values are FULL_REQUEST_CACHING or PER_RESOLVER_CACHING.
            type: The cache instance type. Valid values are SMALL, MEDIUM, LARGE, XLARGE,
                  LARGE_2X, LARGE_4X, LARGE_8X (not available in all regions), LARGE_12X.
            transit_encryption_enabled: Optional flag to enable transit encryption when connecting to cache.
            at_rest_encryption_enabled: Optional flag to enable at-rest encryption for cache.
            health_metrics_config: Optional health metrics configuration. Valid values are ENABLED or DISABLED.

        Returns:
            A dictionary containing information about the created API cache, including:
            - apiCache: The API cache object with details like status, type, ttl, etc.

        Example response:
            {
                "apiCache": {
                    "ttl": 300,
                    "apiCachingBehavior": "FULL_REQUEST_CACHING",
                    "transitEncryptionEnabled": true,
                    "atRestEncryptionEnabled": true,
                    "type": "SMALL",
                    "status": "CREATING",
                    "healthMetricsConfig": "ENABLED"
                }
            }
        """
        return await create_api_cache_operation(
            api_id,
            ttl,
            api_caching_behavior,
            type,
            transit_encryption_enabled,
            at_rest_encryption_enabled,
            health_metrics_config,
        )
