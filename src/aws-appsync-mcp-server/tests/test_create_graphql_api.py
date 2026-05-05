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

"""Tests for the create_graphql_api operation."""

import pytest
from awslabs.aws_appsync_mcp_server.operations.create_graphql_api import (
    _validate_inputs,
    create_graphql_api_operation,
)
from awslabs.aws_appsync_mcp_server.tools.create_graphql_api import (
    register_create_graphql_api_tool,
)
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_create_graphql_api_minimal_non_api_key():
    """Test create_graphql_api tool with minimal parameters (non-API_KEY auth)."""
    mock_client = MagicMock()
    mock_response = {
        'graphqlApi': {
            'name': 'test-graphql-api',
            'apiId': 'test-graphql-api-id',
            'authenticationType': 'AWS_IAM',
            'arn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-graphql-api-id',
            'uris': {
                'GRAPHQL': 'https://test-graphql-api-id.appsync-api.us-east-1.amazonaws.com/graphql'
            },
            'creationTime': '2024-01-01T00:00:00Z',
            'xrayEnabled': False,
        }
    }
    mock_client.create_graphql_api.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_graphql_api_operation(
            name='test-graphql-api', authentication_type='AWS_IAM'
        )

        mock_client.create_graphql_api.assert_called_once_with(
            name='test-graphql-api', authenticationType='AWS_IAM'
        )
        assert result == mock_response
        # Should not contain apiKey for non-API_KEY auth
        assert 'apiKey' not in result


@pytest.mark.asyncio
async def test_create_graphql_api_with_api_key_auth():
    """Test create_graphql_api tool with API_KEY authentication creates API key automatically."""
    mock_client = MagicMock()
    mock_graphql_response = {
        'graphqlApi': {
            'name': 'test-graphql-api',
            'apiId': 'test-graphql-api-id',
            'authenticationType': 'API_KEY',
            'arn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-graphql-api-id',
            'uris': {
                'GRAPHQL': 'https://test-graphql-api-id.appsync-api.us-east-1.amazonaws.com/graphql'
            },
            'creationTime': '2024-01-01T00:00:00Z',
            'xrayEnabled': False,
        }
    }
    mock_client.create_graphql_api.return_value = mock_graphql_response

    mock_api_key_response = {
        'apiKey': {
            'id': 'da2-abcdefghijklmnopqrstuvwxyz',  # pragma: allowlist secret
            'description': 'Auto-generated API key',
        }  # pragma: allowlist secret
    }

    with (
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.get_appsync_client',
            return_value=mock_client,
        ),
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.create_api_key_operation',
            new_callable=AsyncMock,
            return_value=mock_api_key_response,
        ) as mock_create_api_key,
    ):
        result = await create_graphql_api_operation(
            name='test-graphql-api', authentication_type='API_KEY'
        )

        # Verify GraphQL API creation
        mock_client.create_graphql_api.assert_called_once_with(
            name='test-graphql-api', authenticationType='API_KEY'
        )

        # Verify API key creation
        mock_create_api_key.assert_called_once_with(
            api_id='test-graphql-api-id', description='Auto-generated API key'
        )

        # Verify result contains both GraphQL API and API key
        expected_result = {
            'graphqlApi': mock_graphql_response['graphqlApi'],
            'apiKey': mock_api_key_response['apiKey'],
        }
        assert result == expected_result


@pytest.mark.asyncio
async def test_create_graphql_api_api_key_auth_missing_api_id():
    """Test create_graphql_api with API_KEY auth when API ID is missing from response."""
    mock_client = MagicMock()
    mock_response = {
        'graphqlApi': {
            'name': 'test-graphql-api',
            'authenticationType': 'API_KEY',
            # Missing apiId
        }
    }
    mock_client.create_graphql_api.return_value = mock_response

    with (
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.get_appsync_client',
            return_value=mock_client,
        ),
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.create_api_key_operation',
            new_callable=AsyncMock,
        ) as mock_create_api_key,
    ):
        result = await create_graphql_api_operation(
            name='test-graphql-api', authentication_type='API_KEY'
        )

        # Should not attempt to create API key if apiId is missing
        mock_create_api_key.assert_not_called()
        assert result == mock_response
        assert 'apiKey' not in result


@pytest.mark.asyncio
async def test_create_graphql_api_full():
    """Test create_graphql_api tool with all parameters."""
    mock_client = MagicMock()
    mock_response = {
        'graphqlApi': {
            'name': 'test-graphql-api',
            'apiId': 'test-graphql-api-id',
            'authenticationType': 'AMAZON_COGNITO_USER_POOLS',
            'arn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-graphql-api-id',
            'uris': {
                'GRAPHQL': 'https://test-graphql-api-id.appsync-api.us-east-1.amazonaws.com/graphql'
            },
            'userPoolConfig': {
                'userPoolId': 'us-east-1_test',
                'awsRegion': 'us-east-1',
                'defaultAction': 'ALLOW',
            },
            'tags': {'Environment': 'test'},
            'creationTime': '2024-01-01T00:00:00Z',
            'xrayEnabled': True,
        }
    }
    mock_client.create_graphql_api.return_value = mock_response

    log_config = {
        'fieldLogLevel': 'ALL',
        'cloudWatchLogsRoleArn': 'arn:aws:iam::123456789012:role/service-role/appsync-logs',
    }
    user_pool_config = {
        'userPoolId': 'us-east-1_test',
        'awsRegion': 'us-east-1',
        'defaultAction': 'ALLOW',
    }
    tags = {'Environment': 'test'}
    additional_auth_providers = [{'authenticationType': 'API_KEY'}]
    enhanced_metrics_config = {
        'resolverLevelMetricsBehavior': 'FULL_REQUEST_RESOLVER_METRICS',
        'dataSourceLevelMetricsBehavior': 'FULL_REQUEST_DATA_SOURCE_METRICS',
        'operationLevelMetricsConfig': 'ENABLED',
    }

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_graphql_api_operation(
            name='test-graphql-api',
            authentication_type='AMAZON_COGNITO_USER_POOLS',
            log_config=log_config,
            user_pool_config=user_pool_config,
            tags=tags,
            additional_authentication_providers=additional_auth_providers,
            xray_enabled=True,
            visibility='GLOBAL',
            api_type='GRAPHQL',
            owner_contact='test@example.com',
            introspection_config='ENABLED',
            query_depth_limit=10,
            resolver_count_limit=100,
            enhanced_metrics_config=enhanced_metrics_config,
        )

        mock_client.create_graphql_api.assert_called_once_with(
            name='test-graphql-api',
            authenticationType='AMAZON_COGNITO_USER_POOLS',
            logConfig=log_config,
            userPoolConfig=user_pool_config,
            tags=tags,
            additionalAuthenticationProviders=additional_auth_providers,
            xrayEnabled=True,
            visibility='GLOBAL',
            apiType='GRAPHQL',
            ownerContact='test@example.com',
            introspectionConfig='ENABLED',
            queryDepthLimit=10,
            resolverCountLimit=100,
            enhancedMetricsConfig=enhanced_metrics_config,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_graphql_api_with_openid_connect():
    """Test create_graphql_api tool with OpenID Connect authentication."""
    mock_client = MagicMock()
    mock_response = {
        'graphqlApi': {
            'name': 'test-openid-api',
            'apiId': 'test-openid-api-id',
            'authenticationType': 'OPENID_CONNECT',
            'arn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-openid-api-id',
            'openIDConnectConfig': {'issuer': 'https://example.com', 'clientId': 'test-client-id'},
        }
    }
    mock_client.create_graphql_api.return_value = mock_response

    openid_config = {'issuer': 'https://example.com', 'clientId': 'test-client-id'}

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_graphql_api_operation(
            name='test-openid-api',
            authentication_type='OPENID_CONNECT',
            open_id_connect_config=openid_config,
        )

        mock_client.create_graphql_api.assert_called_once_with(
            name='test-openid-api',
            authenticationType='OPENID_CONNECT',
            openIDConnectConfig=openid_config,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_graphql_api_with_lambda_auth():
    """Test create_graphql_api tool with Lambda authorization."""
    mock_client = MagicMock()
    mock_response = {
        'graphqlApi': {
            'name': 'test-lambda-api',
            'apiId': 'test-lambda-api-id',
            'authenticationType': 'AWS_LAMBDA',
            'arn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-lambda-api-id',
            'lambdaAuthorizerConfig': {
                'authorizerUri': 'arn:aws:lambda:us-east-1:123456789012:function:test-authorizer'
            },
        }
    }
    mock_client.create_graphql_api.return_value = mock_response

    lambda_config = {
        'authorizerUri': 'arn:aws:lambda:us-east-1:123456789012:function:test-authorizer',
        'authorizerResultTtlInSeconds': 300,
    }

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_graphql_api_operation(
            name='test-lambda-api',
            authentication_type='AWS_LAMBDA',
            lambda_authorizer_config=lambda_config,
        )

        mock_client.create_graphql_api.assert_called_once_with(
            name='test-lambda-api',
            authenticationType='AWS_LAMBDA',
            lambdaAuthorizerConfig=lambda_config,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_graphql_api_merged_api():
    """Test create_graphql_api tool with merged API configuration."""
    mock_client = MagicMock()
    mock_response = {
        'graphqlApi': {
            'name': 'test-merged-api',
            'apiId': 'test-merged-api-id',
            'authenticationType': 'AWS_IAM',
            'arn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-merged-api-id',
            'apiType': 'MERGED',
            'mergedApiExecutionRoleArn': 'arn:aws:iam::123456789012:role/appsync-merged-api-role',
        }
    }
    mock_client.create_graphql_api.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_graphql_api_operation(
            name='test-merged-api',
            authentication_type='AWS_IAM',
            api_type='MERGED',
            merged_api_execution_role_arn='arn:aws:iam::123456789012:role/appsync-merged-api-role',
        )

        mock_client.create_graphql_api.assert_called_once_with(
            name='test-merged-api',
            authenticationType='AWS_IAM',
            apiType='MERGED',
            mergedApiExecutionRoleArn='arn:aws:iam::123456789012:role/appsync-merged-api-role',
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_graphql_api_api_key_auth_with_additional_params():
    """Test create_graphql_api with API_KEY auth and additional parameters."""
    mock_client = MagicMock()
    mock_graphql_response = {
        'graphqlApi': {
            'name': 'test-api-with-params',
            'apiId': 'test-api-id-123',
            'authenticationType': 'API_KEY',
            'arn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id-123',
            'tags': {'Environment': 'test'},
            'xrayEnabled': True,
        }
    }
    mock_client.create_graphql_api.return_value = mock_graphql_response

    mock_api_key_response = {
        'apiKey': {'id': 'da2-testkey123', 'description': 'Auto-generated API key'}
    }

    tags = {'Environment': 'test'}
    log_config = {'fieldLogLevel': 'ALL'}

    with (
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.get_appsync_client',
            return_value=mock_client,
        ),
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.create_api_key_operation',
            new_callable=AsyncMock,
            return_value=mock_api_key_response,
        ) as mock_create_api_key,
    ):
        result = await create_graphql_api_operation(
            name='test-api-with-params',
            authentication_type='API_KEY',
            tags=tags,
            log_config=log_config,
            xray_enabled=True,
        )

        # Verify GraphQL API creation with all parameters
        mock_client.create_graphql_api.assert_called_once_with(
            name='test-api-with-params',
            authenticationType='API_KEY',
            tags=tags,
            logConfig=log_config,
            xrayEnabled=True,
        )

        # Verify API key creation
        mock_create_api_key.assert_called_once_with(
            api_id='test-api-id-123', description='Auto-generated API key'
        )

        # Verify result
        expected_result = {
            'graphqlApi': mock_graphql_response['graphqlApi'],
            'apiKey': mock_api_key_response['apiKey'],
        }
        assert result == expected_result


@pytest.mark.asyncio
async def test_create_graphql_api_api_key_creation_failure():
    """Test create_graphql_api when API key creation fails."""
    mock_client = MagicMock()
    mock_graphql_response = {
        'graphqlApi': {
            'name': 'test-graphql-api',
            'apiId': 'test-graphql-api-id',
            'authenticationType': 'API_KEY',
        }
    }
    mock_client.create_graphql_api.return_value = mock_graphql_response

    with (
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.get_appsync_client',
            return_value=mock_client,
        ),
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.create_api_key_operation',
            new_callable=AsyncMock,
            side_effect=Exception('API key creation failed'),
        ),
    ):
        # Should propagate the exception from API key creation
        with pytest.raises(Exception, match='API key creation failed'):
            await create_graphql_api_operation(
                name='test-graphql-api', authentication_type='API_KEY'
            )


@pytest.mark.asyncio
async def test_create_graphql_api_multiple_auth_types():
    """Test create_graphql_api with different authentication types to ensure API key is only created for API_KEY."""
    auth_types = ['AWS_IAM', 'AMAZON_COGNITO_USER_POOLS', 'OPENID_CONNECT', 'AWS_LAMBDA']

    for auth_type in auth_types:
        mock_client = MagicMock()
        mock_response = {
            'graphqlApi': {
                'name': f'test-api-{auth_type.lower()}',
                'apiId': f'test-api-id-{auth_type.lower()}',
                'authenticationType': auth_type,
            }
        }
        mock_client.create_graphql_api.return_value = mock_response

        with (
            patch(
                'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.get_appsync_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.create_api_key_operation',
                new_callable=AsyncMock,
            ) as mock_create_api_key,
        ):
            result = await create_graphql_api_operation(
                name=f'test-api-{auth_type.lower()}', authentication_type=auth_type
            )

            # Should not create API key for non-API_KEY auth types
            mock_create_api_key.assert_not_called()
            assert result == mock_response
            assert 'apiKey' not in result


@pytest.mark.asyncio
async def test_create_graphql_api_api_key_empty_response():
    """Test create_graphql_api with API_KEY auth when create_api_key returns empty response."""
    mock_client = MagicMock()
    mock_graphql_response = {
        'graphqlApi': {
            'name': 'test-graphql-api',
            'apiId': 'test-graphql-api-id',
            'authenticationType': 'API_KEY',
        }
    }
    mock_client.create_graphql_api.return_value = mock_graphql_response

    # Empty API key response
    mock_api_key_response = {}

    with (
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.get_appsync_client',
            return_value=mock_client,
        ),
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_graphql_api.create_api_key_operation',
            new_callable=AsyncMock,
            return_value=mock_api_key_response,
        ) as mock_create_api_key,
    ):
        result = await create_graphql_api_operation(
            name='test-graphql-api', authentication_type='API_KEY'
        )

        # Verify API key creation was attempted
        mock_create_api_key.assert_called_once()

        # Verify result contains empty apiKey
        expected_result = {'graphqlApi': mock_graphql_response['graphqlApi'], 'apiKey': {}}
        assert result == expected_result


def test_register_create_graphql_api_tool():
    """Test that create_graphql_api tool is registered correctly."""
    mock_mcp = MagicMock()
    register_create_graphql_api_tool(mock_mcp)
    mock_mcp.tool.assert_called_once()


@pytest.mark.asyncio
async def test_create_graphql_api_tool_execution():
    """Test create_graphql_api tool execution through MCP."""
    from awslabs.aws_appsync_mcp_server.decorators import set_write_allowed
    from typing import Any, Callable

    mock_mcp = MagicMock()
    captured_func: Callable[..., Any] | None = None

    def capture_tool(**kwargs):
        def decorator(func):
            nonlocal captured_func
            captured_func = func
            return func

        return decorator

    mock_mcp.tool = capture_tool
    set_write_allowed(True)

    register_create_graphql_api_tool(mock_mcp)

    with patch(
        'awslabs.aws_appsync_mcp_server.tools.create_graphql_api.create_graphql_api_operation'
    ) as mock_op:
        mock_op.return_value = {'graphqlApi': {'name': 'test-api'}}
        if captured_func is not None:
            result = await captured_func('test-api', 'API_KEY')
            mock_op.assert_called_once()
            assert result == {'graphqlApi': {'name': 'test-api'}}


class TestValidateInputs:
    """Test cases for input validation."""

    def test_validate_inputs_valid_minimal(self):
        """Test validation with minimal valid inputs."""
        # Should not raise any exception
        _validate_inputs('test-api', 'API_KEY', None, None, None, None, None, None)

    def test_validate_inputs_empty_name(self):
        """Test validation fails with empty name."""
        with pytest.raises(ValueError, match='Name is required and cannot be empty'):
            _validate_inputs('', 'API_KEY', None, None, None, None, None, None)

    def test_validate_inputs_whitespace_name(self):
        """Test validation fails with whitespace-only name."""
        with pytest.raises(ValueError, match='Name is required and cannot be empty'):
            _validate_inputs('   ', 'API_KEY', None, None, None, None, None, None)

    def test_validate_inputs_name_too_long(self):
        """Test validation fails with name exceeding 65536 characters."""
        long_name = 'a' * 65537
        with pytest.raises(ValueError, match='Name cannot exceed 65536 characters'):
            _validate_inputs(long_name, 'API_KEY', None, None, None, None, None, None)

    def test_validate_inputs_invalid_auth_type(self):
        """Test validation fails with invalid authentication type."""
        with pytest.raises(ValueError, match='Invalid authentication_type'):
            _validate_inputs('test-api', 'INVALID_AUTH', None, None, None, None, None, None)

    def test_validate_inputs_valid_auth_types(self):
        """Test validation passes with all valid authentication types."""
        valid_types = [
            'API_KEY',
            'AWS_IAM',
            'AMAZON_COGNITO_USER_POOLS',
            'OPENID_CONNECT',
            'AWS_LAMBDA',
        ]
        for auth_type in valid_types:
            _validate_inputs('test-api', auth_type, None, None, None, None, None, None)

    def test_validate_inputs_invalid_visibility(self):
        """Test validation fails with invalid visibility."""
        with pytest.raises(ValueError, match="Invalid visibility. Must be 'GLOBAL' or 'PRIVATE'"):
            _validate_inputs('test-api', 'API_KEY', 'INVALID', None, None, None, None, None)

    def test_validate_inputs_valid_visibility(self):
        """Test validation passes with valid visibility values."""
        for visibility in ['GLOBAL', 'PRIVATE']:
            _validate_inputs('test-api', 'API_KEY', visibility, None, None, None, None, None)

    def test_validate_inputs_invalid_api_type(self):
        """Test validation fails with invalid API type."""
        with pytest.raises(ValueError, match="Invalid api_type. Must be 'GRAPHQL' or 'MERGED'"):
            _validate_inputs('test-api', 'API_KEY', None, 'INVALID', None, None, None, None)

    def test_validate_inputs_valid_api_type(self):
        """Test validation passes with valid API types."""
        for api_type in ['GRAPHQL', 'MERGED']:
            _validate_inputs('test-api', 'API_KEY', None, api_type, None, None, None, None)

    def test_validate_inputs_invalid_introspection_config(self):
        """Test validation fails with invalid introspection config."""
        with pytest.raises(
            ValueError, match="Invalid introspection_config. Must be 'ENABLED' or 'DISABLED'"
        ):
            _validate_inputs('test-api', 'API_KEY', None, None, 'INVALID', None, None, None)

    def test_validate_inputs_valid_introspection_config(self):
        """Test validation passes with valid introspection config values."""
        for config in ['ENABLED', 'DISABLED']:
            _validate_inputs('test-api', 'API_KEY', None, None, config, None, None, None)

    def test_validate_inputs_query_depth_limit_negative(self):
        """Test validation fails with negative query depth limit."""
        with pytest.raises(ValueError, match='query_depth_limit must be between 0 and 75'):
            _validate_inputs('test-api', 'API_KEY', None, None, None, -1, None, None)

    def test_validate_inputs_query_depth_limit_too_high(self):
        """Test validation fails with query depth limit exceeding 75."""
        with pytest.raises(ValueError, match='query_depth_limit must be between 0 and 75'):
            _validate_inputs('test-api', 'API_KEY', None, None, None, 76, None, None)

    def test_validate_inputs_valid_query_depth_limits(self):
        """Test validation passes with valid query depth limits."""
        for limit in [0, 1, 75]:
            _validate_inputs('test-api', 'API_KEY', None, None, None, limit, None, None)

    def test_validate_inputs_resolver_count_limit_negative(self):
        """Test validation fails with negative resolver count limit."""
        with pytest.raises(ValueError, match='resolver_count_limit must be between 0 and 10000'):
            _validate_inputs('test-api', 'API_KEY', None, None, None, None, -1, None)

    def test_validate_inputs_resolver_count_limit_too_high(self):
        """Test validation fails with resolver count limit exceeding 10000."""
        with pytest.raises(ValueError, match='resolver_count_limit must be between 0 and 10000'):
            _validate_inputs('test-api', 'API_KEY', None, None, None, None, 10001, None)

    def test_validate_inputs_valid_resolver_count_limits(self):
        """Test validation passes with valid resolver count limits."""
        for limit in [0, 1, 10000]:
            _validate_inputs('test-api', 'API_KEY', None, None, None, None, limit, None)

    def test_validate_inputs_invalid_arn_format(self):
        """Test validation fails with invalid ARN format."""
        invalid_arns = [
            'invalid-arn',
            'arn:aws:s3:::bucket',  # Wrong service
            'arn:aws:iam::123456789012:user/test',  # Wrong resource type
            'arn:aws:iam::invalid:role/test',  # Invalid account ID
        ]
        for arn in invalid_arns:
            with pytest.raises(ValueError, match='Invalid merged_api_execution_role_arn format'):
                _validate_inputs('test-api', 'API_KEY', None, None, None, None, None, arn)

    def test_validate_inputs_valid_arn_formats(self):
        """Test validation passes with valid ARN formats."""
        valid_arns = [
            'arn:aws:iam::123456789012:role/test-role',
            'arn:aws-us-gov:iam::123456789012:role/gov-role',
            'arn:aws-cn:iam::123456789012:role/china-role',
        ]
        for arn in valid_arns:
            _validate_inputs('test-api', 'API_KEY', None, None, None, None, None, arn)

    def test_validate_inputs_all_valid_parameters(self):
        """Test validation passes with all valid parameters."""
        _validate_inputs(
            name='test-api',
            authentication_type='API_KEY',
            visibility='GLOBAL',
            api_type='GRAPHQL',
            introspection_config='ENABLED',
            query_depth_limit=50,
            resolver_count_limit=5000,
            merged_api_execution_role_arn='arn:aws:iam::123456789012:role/test-role',
        )
