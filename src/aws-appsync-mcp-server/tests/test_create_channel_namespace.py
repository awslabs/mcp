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

"""Tests for create_channel_namespace operation."""

import pytest
from awslabs.aws_appsync_mcp_server.operations.create_channel_namespace import (
    create_channel_namespace_operation,
)
from awslabs.aws_appsync_mcp_server.tools.create_channel_namespace import (
    register_create_channel_namespace_tool,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_create_channel_namespace_minimal():
    """Test create_channel_namespace tool with minimal required parameters."""
    mock_client = MagicMock()
    mock_response = {
        'channelNamespace': {
            'apiId': 'test-api-id',
            'name': 'test-namespace',
            'channelNamespaceArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/channelNamespace/test-namespace',
            'creationDate': '2023-01-01T00:00:00Z',
            'lastModifiedDate': '2023-01-01T00:00:00Z',
        }
    }
    mock_client.create_channel_namespace.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_channel_namespace.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_channel_namespace_operation(
            api_id='test-api-id', name='test-namespace'
        )

        mock_client.create_channel_namespace.assert_called_once_with(
            apiId='test-api-id', name='test-namespace'
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_channel_namespace_with_handler_configs():
    """Test create_channel_namespace tool with handler configs."""
    mock_client = MagicMock()
    mock_response = {
        'channelNamespace': {
            'apiId': 'test-api-id',
            'name': 'test-namespace',
            'channelNamespaceArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/channelNamespace/test-namespace',
            'handlerConfigs': {
                'onSubscribe': {
                    'behavior': 'CODE',
                    'integration': {
                        'dataSourceName': 'my-subscribe-datasource',
                        'lambdaConfig': {'invokeType': 'REQUEST_RESPONSE'},
                    },
                },
                'onPublish': {
                    'behavior': 'DIRECT',
                    'integration': {
                        'dataSourceName': 'my-publish-datasource',
                        'lambdaConfig': {'invokeType': 'EVENT'},
                    },
                },
            },
            'creationDate': '2023-01-01T00:00:00Z',
            'lastModifiedDate': '2023-01-01T00:00:00Z',
        }
    }
    mock_client.create_channel_namespace.return_value = mock_response

    handler_configs = {
        'onSubscribe': {
            'behavior': 'CODE',
            'integration': {
                'dataSourceName': 'my-subscribe-datasource',
                'lambdaConfig': {'invokeType': 'REQUEST_RESPONSE'},
            },
        },
        'onPublish': {
            'behavior': 'DIRECT',
            'integration': {
                'dataSourceName': 'my-publish-datasource',
                'lambdaConfig': {'invokeType': 'EVENT'},
            },
        },
    }

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_channel_namespace.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_channel_namespace_operation(
            api_id='test-api-id', name='test-namespace', handler_configs=handler_configs
        )

        mock_client.create_channel_namespace.assert_called_once_with(
            apiId='test-api-id', name='test-namespace', handlerConfigs=handler_configs
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_channel_namespace_with_auth_modes():
    """Test create_channel_namespace tool with auth modes."""
    mock_client = MagicMock()
    mock_response = {
        'channelNamespace': {
            'apiId': 'test-api-id',
            'name': 'test-namespace',
            'channelNamespaceArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/channelNamespace/test-namespace',
            'subscribeAuthModes': [{'authType': 'API_KEY'}, {'authType': 'AWS_IAM'}],
            'publishAuthModes': [
                {'authType': 'AMAZON_COGNITO_USER_POOLS'},
                {'authType': 'AWS_IAM'},
            ],
            'creationDate': '2023-01-01T00:00:00Z',
            'lastModifiedDate': '2023-01-01T00:00:00Z',
        }
    }
    mock_client.create_channel_namespace.return_value = mock_response

    subscribe_auth_modes = [{'authType': 'API_KEY'}, {'authType': 'AWS_IAM'}]
    publish_auth_modes = [{'authType': 'AMAZON_COGNITO_USER_POOLS'}, {'authType': 'AWS_IAM'}]

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_channel_namespace.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_channel_namespace_operation(
            api_id='test-api-id',
            name='test-namespace',
            subscribe_auth_modes=subscribe_auth_modes,
            publish_auth_modes=publish_auth_modes,
        )

        mock_client.create_channel_namespace.assert_called_once_with(
            apiId='test-api-id',
            name='test-namespace',
            subscribeAuthModes=subscribe_auth_modes,
            publishAuthModes=publish_auth_modes,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_channel_namespace_full_configuration():
    """Test create_channel_namespace tool with all optional parameters."""
    mock_client = MagicMock()
    mock_response = {
        'channelNamespace': {
            'apiId': 'test-api-id',
            'name': 'test-full-namespace',
            'channelNamespaceArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/channelNamespace/test-full-namespace',
            'subscribeAuthModes': [{'authType': 'API_KEY'}, {'authType': 'AWS_IAM'}],
            'publishAuthModes': [
                {'authType': 'AMAZON_COGNITO_USER_POOLS'},
                {'authType': 'AWS_IAM'},
            ],
            'codeHandlers': 'export function onSubscribe() { return {}; } export function onPublish(ctx) { return ctx.event; }',
            'handlerConfigs': {
                'onSubscribe': {
                    'behavior': 'CODE',
                    'integration': {
                        'dataSourceName': 'my-subscribe-datasource',
                        'lambdaConfig': {'invokeType': 'REQUEST_RESPONSE'},
                    },
                }
            },
            'tags': {'Environment': 'production', 'Team': 'backend', 'Project': 'realtime-chat'},
            'creationDate': '2023-01-01T00:00:00Z',
            'lastModifiedDate': '2023-01-01T00:00:00Z',
        }
    }
    mock_client.create_channel_namespace.return_value = mock_response

    subscribe_auth_modes = [{'authType': 'API_KEY'}, {'authType': 'AWS_IAM'}]
    publish_auth_modes = [{'authType': 'AMAZON_COGNITO_USER_POOLS'}, {'authType': 'AWS_IAM'}]
    code_handlers = 'export function onSubscribe() { return {}; } export function onPublish(ctx) { return ctx.event; }'
    handler_configs = {
        'onSubscribe': {
            'behavior': 'CODE',
            'integration': {
                'dataSourceName': 'my-subscribe-datasource',
                'lambdaConfig': {'invokeType': 'REQUEST_RESPONSE'},
            },
        }
    }
    tags = {'Environment': 'production', 'Team': 'backend', 'Project': 'realtime-chat'}

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_channel_namespace.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_channel_namespace_operation(
            api_id='test-api-id',
            name='test-full-namespace',
            subscribe_auth_modes=subscribe_auth_modes,
            publish_auth_modes=publish_auth_modes,
            code_handlers=code_handlers,
            handler_configs=handler_configs,
            tags=tags,
        )

        mock_client.create_channel_namespace.assert_called_once_with(
            apiId='test-api-id',
            name='test-full-namespace',
            subscribeAuthModes=subscribe_auth_modes,
            publishAuthModes=publish_auth_modes,
            codeHandlers=code_handlers,
            handlerConfigs=handler_configs,
            tags=tags,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_channel_namespace_empty_response():
    """Test create_channel_namespace tool with empty response from AWS."""
    mock_client = MagicMock()
    mock_response = {'channelNamespace': {}}
    mock_client.create_channel_namespace.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_channel_namespace.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_channel_namespace_operation(
            api_id='test-api-id', name='test-namespace'
        )

        mock_client.create_channel_namespace.assert_called_once_with(
            apiId='test-api-id', name='test-namespace'
        )
        assert result == mock_response


def test_register_create_channel_namespace_tool():
    """Test that create_channel_namespace tool is registered correctly."""
    mock_mcp = MagicMock()
    register_create_channel_namespace_tool(mock_mcp)
    mock_mcp.tool.assert_called_once()


@pytest.mark.asyncio
async def test_create_channel_namespace_tool_execution():
    """Test create_channel_namespace tool execution through MCP."""
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

    register_create_channel_namespace_tool(mock_mcp)

    with patch(
        'awslabs.aws_appsync_mcp_server.tools.create_channel_namespace.create_channel_namespace_operation'
    ) as mock_op:
        mock_op.return_value = {'channelNamespace': {'name': 'test-ns'}}
        if captured_func is not None:
            result = await captured_func('test-api', 'test-ns')
            mock_op.assert_called_once_with('test-api', 'test-ns', None, None, None, None, None)
            assert result == {'channelNamespace': {'name': 'test-ns'}}
