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

"""Create GraphQL API operation for AWS AppSync MCP Server."""

import re
from awslabs.aws_appsync_mcp_server.helpers import get_appsync_client, handle_exceptions
from awslabs.aws_appsync_mcp_server.operations.create_api_key import create_api_key_operation
from typing import Any, Dict, List, Optional


@handle_exceptions
async def create_graphql_api_operation(
    name: str,
    authentication_type: str,
    log_config: Optional[Dict] = None,
    user_pool_config: Optional[Dict] = None,
    open_id_connect_config: Optional[Dict] = None,
    tags: Optional[Dict[str, str]] = None,
    additional_authentication_providers: Optional[List[Dict]] = None,
    xray_enabled: Optional[bool] = None,
    lambda_authorizer_config: Optional[Dict] = None,
    visibility: Optional[str] = None,
    api_type: Optional[str] = None,
    merged_api_execution_role_arn: Optional[str] = None,
    owner_contact: Optional[str] = None,
    introspection_config: Optional[str] = None,
    query_depth_limit: Optional[int] = None,
    resolver_count_limit: Optional[int] = None,
    enhanced_metrics_config: Optional[Dict] = None,
) -> Dict:
    """Execute create_graphql_api operation."""
    # Input validation
    _validate_inputs(
        name,
        authentication_type,
        visibility,
        api_type,
        introspection_config,
        query_depth_limit,
        resolver_count_limit,
        merged_api_execution_role_arn,
    )

    client = get_appsync_client()

    params: Dict[str, Any] = {'name': name, 'authenticationType': authentication_type}

    if log_config is not None:
        params['logConfig'] = log_config
    if user_pool_config is not None:
        params['userPoolConfig'] = user_pool_config
    if open_id_connect_config is not None:
        params['openIDConnectConfig'] = open_id_connect_config
    if tags is not None:
        params['tags'] = tags
    if additional_authentication_providers is not None:
        params['additionalAuthenticationProviders'] = additional_authentication_providers
    if xray_enabled is not None:
        params['xrayEnabled'] = xray_enabled
    if lambda_authorizer_config is not None:
        params['lambdaAuthorizerConfig'] = lambda_authorizer_config
    if visibility is not None:
        params['visibility'] = visibility
    if api_type is not None:
        params['apiType'] = api_type
    if merged_api_execution_role_arn is not None:
        params['mergedApiExecutionRoleArn'] = merged_api_execution_role_arn
    if owner_contact is not None:
        params['ownerContact'] = owner_contact
    if introspection_config is not None:
        params['introspectionConfig'] = introspection_config
    if query_depth_limit is not None:
        params['queryDepthLimit'] = query_depth_limit
    if resolver_count_limit is not None:
        params['resolverCountLimit'] = resolver_count_limit
    if enhanced_metrics_config is not None:
        params['enhancedMetricsConfig'] = enhanced_metrics_config

    response = client.create_graphql_api(**params)
    result = {'graphqlApi': response.get('graphqlApi', {})}

    # If authentication type is API_KEY, create an API key with default expiry (7 days)
    if authentication_type == 'API_KEY':
        api_id = result['graphqlApi'].get('apiId')
        if api_id:
            api_key_response = await create_api_key_operation(
                api_id=api_id, description='Auto-generated API key'
            )
            result['apiKey'] = api_key_response.get('apiKey', {})

    return result


def _validate_inputs(
    name: str,
    authentication_type: str,
    visibility: Optional[str],
    api_type: Optional[str],
    introspection_config: Optional[str],
    query_depth_limit: Optional[int],
    resolver_count_limit: Optional[int],
    merged_api_execution_role_arn: Optional[str],
) -> None:
    """Validate input parameters."""
    # Name validation
    if not name or not name.strip():
        raise ValueError('Name is required and cannot be empty')
    if len(name) > 65536:
        raise ValueError('Name cannot exceed 65536 characters')

    # Authentication type validation
    valid_auth_types = {
        'API_KEY',
        'AWS_IAM',
        'AMAZON_COGNITO_USER_POOLS',
        'OPENID_CONNECT',
        'AWS_LAMBDA',
    }
    if authentication_type not in valid_auth_types:
        raise ValueError(
            f'Invalid authentication_type. Must be one of: {", ".join(valid_auth_types)}'
        )

    # Visibility validation
    if visibility is not None and visibility not in {'GLOBAL', 'PRIVATE'}:
        raise ValueError("Invalid visibility. Must be 'GLOBAL' or 'PRIVATE'")

    # API type validation
    if api_type is not None and api_type not in {'GRAPHQL', 'MERGED'}:
        raise ValueError("Invalid api_type. Must be 'GRAPHQL' or 'MERGED'")

    # Introspection config validation
    if introspection_config is not None and introspection_config not in {'ENABLED', 'DISABLED'}:
        raise ValueError("Invalid introspection_config. Must be 'ENABLED' or 'DISABLED'")

    # Query depth limit validation
    if query_depth_limit is not None and (query_depth_limit < 0 or query_depth_limit > 75):
        raise ValueError('query_depth_limit must be between 0 and 75')

    # Resolver count limit validation
    if resolver_count_limit is not None and (
        resolver_count_limit < 0 or resolver_count_limit > 10000
    ):
        raise ValueError('resolver_count_limit must be between 0 and 10000')

    # ARN validation for merged API execution role
    if merged_api_execution_role_arn is not None:
        arn_pattern = r'^arn:aws[a-zA-Z-]*:iam::\d{12}:role/.+'
        if not re.match(arn_pattern, merged_api_execution_role_arn):
            raise ValueError(
                'Invalid merged_api_execution_role_arn format. Must be a valid IAM role ARN'
            )
