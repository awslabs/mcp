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

"""Create Function operation for AWS AppSync MCP Server."""

from awslabs.aws_appsync_mcp_server.helpers import get_appsync_client, handle_exceptions
from typing import Any, Dict, Optional


@handle_exceptions
async def create_function_operation(
    api_id: str,
    name: str,
    data_source_name: str,
    description: Optional[str] = None,
    request_mapping_template: Optional[str] = None,
    response_mapping_template: Optional[str] = None,
    function_version: Optional[str] = None,
    sync_config: Optional[Dict] = None,
    max_batch_size: Optional[int] = None,
    runtime: Optional[Dict] = None,
    code: Optional[str] = None,
) -> Dict:
    """Execute create_function operation."""
    client = get_appsync_client()

    params: Dict[str, Any] = {'apiId': api_id, 'name': name, 'dataSourceName': data_source_name}

    if description is not None:
        params['description'] = description
    if request_mapping_template is not None:
        params['requestMappingTemplate'] = request_mapping_template
    if response_mapping_template is not None:
        params['responseMappingTemplate'] = response_mapping_template
    if function_version is not None:
        params['functionVersion'] = function_version
    if sync_config is not None:
        params['syncConfig'] = sync_config
    if max_batch_size is not None:
        params['maxBatchSize'] = max_batch_size
    if runtime is not None:
        params['runtime'] = runtime
    if code is not None:
        params['code'] = code

    response = client.create_function(**params)
    return {'functionConfiguration': response.get('functionConfiguration', {})}
