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

"""Create Channel Namespace operation for AWS AppSync MCP Server."""

from awslabs.aws_appsync_mcp_server.helpers import get_appsync_client, handle_exceptions
from typing import Any, Dict, List, Optional


@handle_exceptions
async def create_channel_namespace_operation(
    api_id: str,
    name: str,
    subscribe_auth_modes: Optional[List[Dict]] = None,
    publish_auth_modes: Optional[List[Dict]] = None,
    code_handlers: Optional[str] = None,
    handler_configs: Optional[Dict] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Dict:
    """Execute create_channel_namespace operation."""
    client = get_appsync_client()

    params: Dict[str, Any] = {'apiId': api_id, 'name': name}

    if subscribe_auth_modes is not None:
        params['subscribeAuthModes'] = subscribe_auth_modes
    if publish_auth_modes is not None:
        params['publishAuthModes'] = publish_auth_modes
    if code_handlers is not None:
        params['codeHandlers'] = code_handlers
    if handler_configs is not None:
        params['handlerConfigs'] = handler_configs
    if tags is not None:
        params['tags'] = tags

    response = client.create_channel_namespace(**params)
    return {'channelNamespace': response.get('channelNamespace', {})}
