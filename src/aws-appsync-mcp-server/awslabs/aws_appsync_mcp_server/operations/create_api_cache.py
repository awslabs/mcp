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

"""Create API Cache operation for AWS AppSync MCP Server."""

from awslabs.aws_appsync_mcp_server.helpers import get_appsync_client, handle_exceptions
from typing import Dict, Optional


@handle_exceptions
async def create_api_cache_operation(
    api_id: str,
    ttl: int,
    api_caching_behavior: str,
    type: str,
    transit_encryption_enabled: Optional[bool] = None,
    at_rest_encryption_enabled: Optional[bool] = None,
    health_metrics_config: Optional[str] = None,
) -> Dict:
    """Execute create_api_cache operation."""
    client = get_appsync_client()

    params = {
        'apiId': api_id,
        'ttl': ttl,
        'apiCachingBehavior': api_caching_behavior,
        'type': type,
    }

    if transit_encryption_enabled is not None:
        params['transitEncryptionEnabled'] = transit_encryption_enabled
    if at_rest_encryption_enabled is not None:
        params['atRestEncryptionEnabled'] = at_rest_encryption_enabled
    if health_metrics_config is not None:
        params['healthMetricsConfig'] = health_metrics_config

    response = client.create_api_cache(**params)
    return {'apiCache': response.get('apiCache', {})}
