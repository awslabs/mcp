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

"""Create API operation for AWS AppSync MCP Server."""

from awslabs.aws_appsync_mcp_server.helpers import get_appsync_client, handle_exceptions
from typing import Any, Dict, Optional


@handle_exceptions
async def create_api_operation(
    name: str,
    owner_contact: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    event_config: Optional[Dict] = None,
) -> Dict:
    """Execute create_api operation."""
    client = get_appsync_client()

    params: Dict[str, Any] = {'name': name}

    if owner_contact is not None:
        params['ownerContact'] = owner_contact
    if tags is not None:
        params['tags'] = tags
    if event_config is not None:
        params['eventConfig'] = event_config

    response = client.create_api(**params)
    return {'api': response.get('api', {})}
