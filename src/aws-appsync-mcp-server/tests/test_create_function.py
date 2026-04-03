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

"""Tests for create_function operation."""

import pytest
from awslabs.aws_appsync_mcp_server.operations.create_function import create_function_operation
from awslabs.aws_appsync_mcp_server.tools.create_function import register_create_function_tool
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_create_function_minimal():
    """Test create_function tool with minimal required parameters."""
    mock_client = MagicMock()
    mock_response = {
        'functionConfiguration': {
            'functionId': 'test-function-id',
            'functionArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/functions/test-function-id',
            'name': 'test-function',
            'dataSourceName': 'test-datasource',
        }
    }
    mock_client.create_function.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_function.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_function_operation(
            api_id='test-api-id', name='test-function', data_source_name='test-datasource'
        )

        mock_client.create_function.assert_called_once_with(
            apiId='test-api-id', name='test-function', dataSourceName='test-datasource'
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_function_with_description():
    """Test create_function tool with description."""
    mock_client = MagicMock()
    mock_response = {
        'functionConfiguration': {
            'functionId': 'test-function-id',
            'functionArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/functions/test-function-id',
            'name': 'test-function',
            'description': 'Test function description',
            'dataSourceName': 'test-datasource',
        }
    }
    mock_client.create_function.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_function.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_function_operation(
            api_id='test-api-id',
            name='test-function',
            data_source_name='test-datasource',
            description='Test function description',
        )

        mock_client.create_function.assert_called_once_with(
            apiId='test-api-id',
            name='test-function',
            dataSourceName='test-datasource',
            description='Test function description',
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_function_with_mapping_templates():
    """Test create_function tool with mapping templates."""
    mock_client = MagicMock()
    mock_response = {
        'functionConfiguration': {
            'functionId': 'test-function-id',
            'functionArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/functions/test-function-id',
            'name': 'test-function',
            'dataSourceName': 'test-datasource',
            'requestMappingTemplate': '{"version": "2018-05-29"}',
            'responseMappingTemplate': '$util.toJson($context.result)',
        }
    }
    mock_client.create_function.return_value = mock_response

    request_template = '{"version": "2018-05-29"}'
    response_template = '$util.toJson($context.result)'

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_function.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_function_operation(
            api_id='test-api-id',
            name='test-function',
            data_source_name='test-datasource',
            request_mapping_template=request_template,
            response_mapping_template=response_template,
        )

        mock_client.create_function.assert_called_once_with(
            apiId='test-api-id',
            name='test-function',
            dataSourceName='test-datasource',
            requestMappingTemplate=request_template,
            responseMappingTemplate=response_template,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_function_with_function_version():
    """Test create_function tool with function version."""
    mock_client = MagicMock()
    mock_response = {
        'functionConfiguration': {
            'functionId': 'test-function-id',
            'functionArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/functions/test-function-id',
            'name': 'test-function',
            'dataSourceName': 'test-datasource',
            'functionVersion': '2018-05-29',
        }
    }
    mock_client.create_function.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_function.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_function_operation(
            api_id='test-api-id',
            name='test-function',
            data_source_name='test-datasource',
            function_version='2018-05-29',
        )

        mock_client.create_function.assert_called_once_with(
            apiId='test-api-id',
            name='test-function',
            dataSourceName='test-datasource',
            functionVersion='2018-05-29',
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_function_with_sync_config():
    """Test create_function tool with sync configuration."""
    mock_client = MagicMock()
    mock_response = {
        'functionConfiguration': {
            'functionId': 'test-function-id',
            'functionArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/functions/test-function-id',
            'name': 'test-function',
            'dataSourceName': 'test-datasource',
            'syncConfig': {
                'conflictHandler': 'OPTIMISTIC_CONCURRENCY',
                'conflictDetection': 'VERSION',
            },
        }
    }
    mock_client.create_function.return_value = mock_response

    sync_config = {'conflictHandler': 'OPTIMISTIC_CONCURRENCY', 'conflictDetection': 'VERSION'}

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_function.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_function_operation(
            api_id='test-api-id',
            name='test-function',
            data_source_name='test-datasource',
            sync_config=sync_config,
        )

        mock_client.create_function.assert_called_once_with(
            apiId='test-api-id',
            name='test-function',
            dataSourceName='test-datasource',
            syncConfig=sync_config,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_function_with_max_batch_size():
    """Test create_function tool with max batch size."""
    mock_client = MagicMock()
    mock_response = {
        'functionConfiguration': {
            'functionId': 'test-function-id',
            'functionArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/functions/test-function-id',
            'name': 'test-function',
            'dataSourceName': 'test-datasource',
            'maxBatchSize': 10,
        }
    }
    mock_client.create_function.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_function.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_function_operation(
            api_id='test-api-id',
            name='test-function',
            data_source_name='test-datasource',
            max_batch_size=10,
        )

        mock_client.create_function.assert_called_once_with(
            apiId='test-api-id',
            name='test-function',
            dataSourceName='test-datasource',
            maxBatchSize=10,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_function_with_runtime():
    """Test create_function tool with runtime configuration."""
    mock_client = MagicMock()
    mock_response = {
        'functionConfiguration': {
            'functionId': 'test-function-id',
            'functionArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/functions/test-function-id',
            'name': 'test-function',
            'dataSourceName': 'test-datasource',
            'runtime': {'name': 'APPSYNC_JS', 'runtimeVersion': '1.0.0'},
        }
    }
    mock_client.create_function.return_value = mock_response

    runtime_config = {'name': 'APPSYNC_JS', 'runtimeVersion': '1.0.0'}

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_function.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_function_operation(
            api_id='test-api-id',
            name='test-function',
            data_source_name='test-datasource',
            runtime=runtime_config,
        )

        mock_client.create_function.assert_called_once_with(
            apiId='test-api-id',
            name='test-function',
            dataSourceName='test-datasource',
            runtime=runtime_config,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_function_with_code():
    """Test create_function tool with code."""
    mock_client = MagicMock()
    mock_response = {
        'functionConfiguration': {
            'functionId': 'test-function-id',
            'functionArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/functions/test-function-id',
            'name': 'test-function',
            'dataSourceName': 'test-datasource',
            'code': 'export function request() { return {}; } export function response(ctx) { return ctx.result; }',
        }
    }
    mock_client.create_function.return_value = mock_response

    function_code = 'export function request() { return {}; } export function response(ctx) { return ctx.result; }'

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_function.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_function_operation(
            api_id='test-api-id',
            name='test-function',
            data_source_name='test-datasource',
            code=function_code,
        )

        mock_client.create_function.assert_called_once_with(
            apiId='test-api-id',
            name='test-function',
            dataSourceName='test-datasource',
            code=function_code,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_function_full_configuration():
    """Test create_function tool with all optional parameters."""
    mock_client = MagicMock()
    mock_response = {
        'functionConfiguration': {
            'functionId': 'test-function-id',
            'functionArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/functions/test-function-id',
            'name': 'test-full-function',
            'description': 'Full configuration test function',
            'dataSourceName': 'test-datasource',
            'requestMappingTemplate': '{"version": "2018-05-29"}',
            'responseMappingTemplate': '$util.toJson($context.result)',
            'functionVersion': '2018-05-29',
            'syncConfig': {
                'conflictHandler': 'OPTIMISTIC_CONCURRENCY',
                'conflictDetection': 'VERSION',
            },
            'maxBatchSize': 10,
            'runtime': {'name': 'APPSYNC_JS', 'runtimeVersion': '1.0.0'},
            'code': 'export function request() { return {}; } export function response(ctx) { return ctx.result; }',
        }
    }
    mock_client.create_function.return_value = mock_response

    sync_config = {'conflictHandler': 'OPTIMISTIC_CONCURRENCY', 'conflictDetection': 'VERSION'}
    runtime_config = {'name': 'APPSYNC_JS', 'runtimeVersion': '1.0.0'}
    function_code = 'export function request() { return {}; } export function response(ctx) { return ctx.result; }'

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_function.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_function_operation(
            api_id='test-api-id',
            name='test-full-function',
            data_source_name='test-datasource',
            description='Full configuration test function',
            request_mapping_template='{"version": "2018-05-29"}',
            response_mapping_template='$util.toJson($context.result)',
            function_version='2018-05-29',
            sync_config=sync_config,
            max_batch_size=10,
            runtime=runtime_config,
            code=function_code,
        )

        mock_client.create_function.assert_called_once_with(
            apiId='test-api-id',
            name='test-full-function',
            dataSourceName='test-datasource',
            description='Full configuration test function',
            requestMappingTemplate='{"version": "2018-05-29"}',
            responseMappingTemplate='$util.toJson($context.result)',
            functionVersion='2018-05-29',
            syncConfig=sync_config,
            maxBatchSize=10,
            runtime=runtime_config,
            code=function_code,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_function_empty_response():
    """Test create_function tool with empty response from AWS."""
    mock_client = MagicMock()
    mock_response = {'functionConfiguration': {}}
    mock_client.create_function.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_function.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_function_operation(
            api_id='test-api-id', name='test-function', data_source_name='test-datasource'
        )

        mock_client.create_function.assert_called_once_with(
            apiId='test-api-id', name='test-function', dataSourceName='test-datasource'
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_function_with_javascript_runtime():
    """Test create_function tool with JavaScript runtime and code."""
    mock_client = MagicMock()
    mock_response = {
        'functionConfiguration': {
            'functionId': 'test-js-function-id',
            'functionArn': 'arn:aws:appsync:us-east-1:123456789012:apis/test-api-id/functions/test-js-function-id',
            'name': 'test-js-function',
            'dataSourceName': 'test-datasource',
            'runtime': {'name': 'APPSYNC_JS', 'runtimeVersion': '1.0.0'},
            'code': """
                export function request(ctx) {
                    return {
                        operation: 'GetItem',
                        key: {
                            id: { S: ctx.args.id }
                        }
                    };
                }

                export function response(ctx) {
                    return ctx.result;
                }
            """,
        }
    }
    mock_client.create_function.return_value = mock_response

    runtime_config = {'name': 'APPSYNC_JS', 'runtimeVersion': '1.0.0'}

    js_code = """
                export function request(ctx) {
                    return {
                        operation: 'GetItem',
                        key: {
                            id: { S: ctx.args.id }
                        }
                    };
                }

                export function response(ctx) {
                    return ctx.result;
                }
            """

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_function.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_function_operation(
            api_id='test-api-id',
            name='test-js-function',
            data_source_name='test-datasource',
            runtime=runtime_config,
            code=js_code,
        )

        mock_client.create_function.assert_called_once_with(
            apiId='test-api-id',
            name='test-js-function',
            dataSourceName='test-datasource',
            runtime=runtime_config,
            code=js_code,
        )
        assert result == mock_response


def test_register_create_function_tool():
    """Test that create_function tool is registered correctly."""
    mock_mcp = MagicMock()
    register_create_function_tool(mock_mcp)
    mock_mcp.tool.assert_called_once()


@pytest.mark.asyncio
async def test_create_function_tool_execution():
    """Test create_function tool execution through MCP."""
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

    register_create_function_tool(mock_mcp)

    with patch(
        'awslabs.aws_appsync_mcp_server.tools.create_function.create_function_operation'
    ) as mock_op:
        mock_op.return_value = {'functionConfiguration': {'name': 'test-fn'}}
        if captured_func is not None:
            result = await captured_func('test-api', 'test-ds', 'test-fn')
            mock_op.assert_called_once()
            assert result == {'functionConfiguration': {'name': 'test-fn'}}
