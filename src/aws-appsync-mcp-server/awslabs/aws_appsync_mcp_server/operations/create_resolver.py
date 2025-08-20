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

"""Create Resolver operation for AWS AppSync MCP Server."""

from awslabs.aws_appsync_mcp_server.helpers import get_appsync_client, handle_exceptions
from typing import Any, Dict, Optional


@handle_exceptions
async def create_resolver_operation(
    api_id: str,
    type_name: str,
    field_name: str,
    data_source_name: Optional[str] = None,
    request_mapping_template: Optional[str] = None,
    response_mapping_template: Optional[str] = None,
    kind: Optional[str] = None,
    pipeline_config: Optional[Dict] = None,
    sync_config: Optional[Dict] = None,
    caching_config: Optional[Dict] = None,
    max_batch_size: Optional[int] = None,
    runtime: Optional[Dict] = None,
    code: Optional[str] = None,
    metrics_config: Optional[str] = None,
) -> Dict:
    """Execute create_resolver operation."""
    client = get_appsync_client()

    params: Dict[str, Any] = {'apiId': api_id, 'typeName': type_name, 'fieldName': field_name}

    if data_source_name is not None:
        params['dataSourceName'] = data_source_name
    if request_mapping_template is not None:
        params['requestMappingTemplate'] = request_mapping_template
    if response_mapping_template is not None:
        params['responseMappingTemplate'] = response_mapping_template
    if kind is not None:
        params['kind'] = kind
    if pipeline_config is not None:
        params['pipelineConfig'] = pipeline_config
    if sync_config is not None:
        params['syncConfig'] = sync_config
    if caching_config is not None:
        params['cachingConfig'] = caching_config
    if max_batch_size is not None:
        params['maxBatchSize'] = max_batch_size
    if runtime is not None:
        params['runtime'] = runtime
    if code is not None:
        params['code'] = code
    if metrics_config is not None:
        params['metricsConfig'] = metrics_config

    response = client.create_resolver(**params)
    return {'resolver': response.get('resolver', {})}
