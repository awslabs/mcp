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

"""Tests for the create_resolver operation."""

import pytest
from awslabs.aws_appsync_mcp_server.operations.create_resolver import create_resolver_operation
from awslabs.aws_appsync_mcp_server.tools.create_resolver import register_create_resolver_tool
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_create_resolver_minimal():
    """Test create_resolver tool with minimal parameters."""
    mock_client = MagicMock()
    mock_response = {
        'resolver': {
            'typeName': 'Query',
            'fieldName': 'getUser',
            'resolverArn': 'arn:aws:appsync:us-east-1:123456789012:apis/abcdefghijklmnopqrstuvwxyz/types/Query/resolvers/getUser',
        }
    }
    mock_client.create_resolver.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_resolver.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_resolver_operation(
            api_id='abcdefghijklmnopqrstuvwxyz', type_name='Query', field_name='getUser'
        )

        mock_client.create_resolver.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz', typeName='Query', fieldName='getUser'
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_resolver_unit_resolver():
    """Test create_resolver tool for unit resolver with data source."""
    mock_client = MagicMock()
    mock_response = {
        'resolver': {
            'typeName': 'Query',
            'fieldName': 'getUser',
            'dataSourceName': 'UserTable',
            'resolverArn': 'arn:aws:appsync:us-east-1:123456789012:apis/abcdefghijklmnopqrstuvwxyz/types/Query/resolvers/getUser',
            'requestMappingTemplate': '{"version": "2017-02-28", "operation": "GetItem", "key": {"id": {"S": "$ctx.args.id"}}}',
            'responseMappingTemplate': '$util.toJson($ctx.result)',
            'kind': 'UNIT',
        }
    }
    mock_client.create_resolver.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_resolver.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_resolver_operation(
            api_id='abcdefghijklmnopqrstuvwxyz',
            type_name='Query',
            field_name='getUser',
            data_source_name='UserTable',
            request_mapping_template='{"version": "2017-02-28", "operation": "GetItem", "key": {"id": {"S": "$ctx.args.id"}}}',
            response_mapping_template='$util.toJson($ctx.result)',
            kind='UNIT',
        )

        mock_client.create_resolver.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz',
            typeName='Query',
            fieldName='getUser',
            dataSourceName='UserTable',
            requestMappingTemplate='{"version": "2017-02-28", "operation": "GetItem", "key": {"id": {"S": "$ctx.args.id"}}}',
            responseMappingTemplate='$util.toJson($ctx.result)',
            kind='UNIT',
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_resolver_pipeline_resolver():
    """Test create_resolver tool for pipeline resolver."""
    mock_client = MagicMock()
    mock_response = {
        'resolver': {
            'typeName': 'Mutation',
            'fieldName': 'createUser',
            'resolverArn': 'arn:aws:appsync:us-east-1:123456789012:apis/abcdefghijklmnopqrstuvwxyz/types/Mutation/resolvers/createUser',
            'kind': 'PIPELINE',
            'pipelineConfig': {'functions': ['function1', 'function2']},
        }
    }
    mock_client.create_resolver.return_value = mock_response

    pipeline_config = {'functions': ['function1', 'function2']}

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_resolver.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_resolver_operation(
            api_id='abcdefghijklmnopqrstuvwxyz',
            type_name='Mutation',
            field_name='createUser',
            kind='PIPELINE',
            pipeline_config=pipeline_config,
        )

        mock_client.create_resolver.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz',
            typeName='Mutation',
            fieldName='createUser',
            kind='PIPELINE',
            pipelineConfig=pipeline_config,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_resolver_with_sync_config():
    """Test create_resolver tool with sync configuration."""
    mock_client = MagicMock()
    mock_response = {
        'resolver': {
            'typeName': 'Mutation',
            'fieldName': 'updateUser',
            'dataSourceName': 'UserTable',
            'resolverArn': 'arn:aws:appsync:us-east-1:123456789012:apis/abcdefghijklmnopqrstuvwxyz/types/Mutation/resolvers/updateUser',
            'syncConfig': {
                'conflictHandler': 'OPTIMISTIC_CONCURRENCY',
                'conflictDetection': 'VERSION',
            },
        }
    }
    mock_client.create_resolver.return_value = mock_response

    sync_config = {'conflictHandler': 'OPTIMISTIC_CONCURRENCY', 'conflictDetection': 'VERSION'}

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_resolver.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_resolver_operation(
            api_id='abcdefghijklmnopqrstuvwxyz',
            type_name='Mutation',
            field_name='updateUser',
            data_source_name='UserTable',
            sync_config=sync_config,
        )

        mock_client.create_resolver.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz',
            typeName='Mutation',
            fieldName='updateUser',
            dataSourceName='UserTable',
            syncConfig=sync_config,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_resolver_with_caching_config():
    """Test create_resolver tool with caching configuration."""
    mock_client = MagicMock()
    mock_response = {
        'resolver': {
            'typeName': 'Query',
            'fieldName': 'getUser',
            'dataSourceName': 'UserTable',
            'resolverArn': 'arn:aws:appsync:us-east-1:123456789012:apis/abcdefghijklmnopqrstuvwxyz/types/Query/resolvers/getUser',
            'cachingConfig': {'ttl': 300, 'cachingKeys': ['$context.arguments.id']},
        }
    }
    mock_client.create_resolver.return_value = mock_response

    caching_config = {'ttl': 300, 'cachingKeys': ['$context.arguments.id']}

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_resolver.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_resolver_operation(
            api_id='abcdefghijklmnopqrstuvwxyz',
            type_name='Query',
            field_name='getUser',
            data_source_name='UserTable',
            caching_config=caching_config,
        )

        mock_client.create_resolver.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz',
            typeName='Query',
            fieldName='getUser',
            dataSourceName='UserTable',
            cachingConfig=caching_config,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_resolver_with_runtime_and_code():
    """Test create_resolver tool with JavaScript/TypeScript runtime and code."""
    mock_client = MagicMock()
    mock_response = {
        'resolver': {
            'typeName': 'Query',
            'fieldName': 'getUser',
            'dataSourceName': 'UserTable',
            'resolverArn': 'arn:aws:appsync:us-east-1:123456789012:apis/abcdefghijklmnopqrstuvwxyz/types/Query/resolvers/getUser',
            'runtime': {'name': 'APPSYNC_JS', 'runtimeVersion': '1.0.0'},
            'code': 'export function request(ctx) { return { operation: "GetItem", key: { id: { S: ctx.args.id } } }; }',
        }
    }
    mock_client.create_resolver.return_value = mock_response

    runtime = {'name': 'APPSYNC_JS', 'runtimeVersion': '1.0.0'}
    code = 'export function request(ctx) { return { operation: "GetItem", key: { id: { S: ctx.args.id } } }; }'

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_resolver.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_resolver_operation(
            api_id='abcdefghijklmnopqrstuvwxyz',
            type_name='Query',
            field_name='getUser',
            data_source_name='UserTable',
            runtime=runtime,
            code=code,
        )

        mock_client.create_resolver.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz',
            typeName='Query',
            fieldName='getUser',
            dataSourceName='UserTable',
            runtime=runtime,
            code=code,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_resolver_with_max_batch_size():
    """Test create_resolver tool with max batch size."""
    mock_client = MagicMock()
    mock_response = {
        'resolver': {
            'typeName': 'Query',
            'fieldName': 'listUsers',
            'dataSourceName': 'UserTable',
            'resolverArn': 'arn:aws:appsync:us-east-1:123456789012:apis/abcdefghijklmnopqrstuvwxyz/types/Query/resolvers/listUsers',
            'maxBatchSize': 10,
        }
    }
    mock_client.create_resolver.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_resolver.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_resolver_operation(
            api_id='abcdefghijklmnopqrstuvwxyz',
            type_name='Query',
            field_name='listUsers',
            data_source_name='UserTable',
            max_batch_size=10,
        )

        mock_client.create_resolver.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz',
            typeName='Query',
            fieldName='listUsers',
            dataSourceName='UserTable',
            maxBatchSize=10,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_resolver_with_metrics_config():
    """Test create_resolver tool with metrics configuration."""
    mock_client = MagicMock()
    mock_response = {
        'resolver': {
            'typeName': 'Query',
            'fieldName': 'getUser',
            'dataSourceName': 'UserTable',
            'resolverArn': 'arn:aws:appsync:us-east-1:123456789012:apis/abcdefghijklmnopqrstuvwxyz/types/Query/resolvers/getUser',
            'metricsConfig': 'ENABLED',
        }
    }
    mock_client.create_resolver.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_resolver.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_resolver_operation(
            api_id='abcdefghijklmnopqrstuvwxyz',
            type_name='Query',
            field_name='getUser',
            data_source_name='UserTable',
            metrics_config='ENABLED',
        )

        mock_client.create_resolver.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz',
            typeName='Query',
            fieldName='getUser',
            dataSourceName='UserTable',
            metricsConfig='ENABLED',
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_resolver_all_parameters():
    """Test create_resolver tool with all parameters."""
    mock_client = MagicMock()
    mock_response = {
        'resolver': {
            'typeName': 'Mutation',
            'fieldName': 'createUser',
            'dataSourceName': 'UserTable',
            'resolverArn': 'arn:aws:appsync:us-east-1:123456789012:apis/abcdefghijklmnopqrstuvwxyz/types/Mutation/resolvers/createUser',
            'requestMappingTemplate': '{"version": "2017-02-28", "operation": "PutItem", "key": {"id": {"S": "$util.autoId()"}}}',
            'responseMappingTemplate': '$util.toJson($ctx.result)',
            'kind': 'UNIT',
            'syncConfig': {
                'conflictHandler': 'OPTIMISTIC_CONCURRENCY',
                'conflictDetection': 'VERSION',
            },
            'cachingConfig': {'ttl': 300, 'cachingKeys': ['$context.arguments.input.name']},
            'maxBatchSize': 5,
            'runtime': {'name': 'APPSYNC_JS', 'runtimeVersion': '1.0.0'},
            'code': 'export function request(ctx) { return { operation: "PutItem", key: { id: { S: util.autoId() } } }; }',
            'metricsConfig': 'ENABLED',
        }
    }
    mock_client.create_resolver.return_value = mock_response

    sync_config = {'conflictHandler': 'OPTIMISTIC_CONCURRENCY', 'conflictDetection': 'VERSION'}
    caching_config = {'ttl': 300, 'cachingKeys': ['$context.arguments.input.name']}
    runtime = {'name': 'APPSYNC_JS', 'runtimeVersion': '1.0.0'}
    code = 'export function request(ctx) { return { operation: "PutItem", key: { id: { S: util.autoId() } } }; }'

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_resolver.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_resolver_operation(
            api_id='abcdefghijklmnopqrstuvwxyz',
            type_name='Mutation',
            field_name='createUser',
            data_source_name='UserTable',
            request_mapping_template='{"version": "2017-02-28", "operation": "PutItem", "key": {"id": {"S": "$util.autoId()"}}}',
            response_mapping_template='$util.toJson($ctx.result)',
            kind='UNIT',
            sync_config=sync_config,
            caching_config=caching_config,
            max_batch_size=5,
            runtime=runtime,
            code=code,
            metrics_config='ENABLED',
        )

        mock_client.create_resolver.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz',
            typeName='Mutation',
            fieldName='createUser',
            dataSourceName='UserTable',
            requestMappingTemplate='{"version": "2017-02-28", "operation": "PutItem", "key": {"id": {"S": "$util.autoId()"}}}',
            responseMappingTemplate='$util.toJson($ctx.result)',
            kind='UNIT',
            syncConfig=sync_config,
            cachingConfig=caching_config,
            maxBatchSize=5,
            runtime=runtime,
            code=code,
            metricsConfig='ENABLED',
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_resolver_empty_response():
    """Test create_resolver tool with empty response."""
    mock_client = MagicMock()
    mock_response = {}
    mock_client.create_resolver.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_resolver.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_resolver_operation(
            api_id='abcdefghijklmnopqrstuvwxyz', type_name='Query', field_name='getUser'
        )

        mock_client.create_resolver.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz', typeName='Query', fieldName='getUser'
        )
        assert result == {'resolver': {}}


def test_register_create_resolver_tool():
    """Test that create_resolver tool is registered correctly."""
    mock_mcp = MagicMock()
    register_create_resolver_tool(mock_mcp)
    mock_mcp.tool.assert_called_once()


@pytest.mark.asyncio
async def test_create_resolver_tool_execution():
    """Test create_resolver tool execution through MCP."""
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

    register_create_resolver_tool(mock_mcp)

    with patch(
        'awslabs.aws_appsync_mcp_server.tools.create_resolver.create_resolver_operation'
    ) as mock_op:
        mock_op.return_value = {'resolver': {'typeName': 'Query'}}
        if captured_func is not None:
            result = await captured_func('test-api', 'Query', 'getUser')
            mock_op.assert_called_once()
            assert result == {'resolver': {'typeName': 'Query'}}
