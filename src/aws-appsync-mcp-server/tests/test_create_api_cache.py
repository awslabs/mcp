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

"""Tests for the create_api_cache operation."""

import pytest
from awslabs.aws_appsync_mcp_server.operations.create_api_cache import create_api_cache_operation
from awslabs.aws_appsync_mcp_server.tools.create_api_cache import register_create_api_cache_tool
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_create_api_cache_minimal():
    """Test create_api_cache tool with minimal parameters."""
    mock_client = MagicMock()
    mock_response = {
        'apiCache': {
            'ttl': 300,
            'apiCachingBehavior': 'FULL_REQUEST_CACHING',
            'type': 'SMALL',
            'status': 'CREATING',
        }
    }
    mock_client.create_api_cache.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_api_cache.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_api_cache_operation(
            api_id='test-api-id',
            ttl=300,
            api_caching_behavior='FULL_REQUEST_CACHING',
            type='SMALL',
        )

        mock_client.create_api_cache.assert_called_once_with(
            apiId='test-api-id', ttl=300, apiCachingBehavior='FULL_REQUEST_CACHING', type='SMALL'
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_api_cache_with_encryption():
    """Test create_api_cache tool with encryption options."""
    mock_client = MagicMock()
    mock_response = {
        'apiCache': {
            'ttl': 600,
            'apiCachingBehavior': 'PER_RESOLVER_CACHING',
            'type': 'MEDIUM',
            'status': 'CREATING',
            'transitEncryptionEnabled': True,
            'atRestEncryptionEnabled': True,
        }
    }
    mock_client.create_api_cache.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_api_cache.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_api_cache_operation(
            api_id='test-api-id',
            ttl=600,
            api_caching_behavior='PER_RESOLVER_CACHING',
            type='MEDIUM',
            transit_encryption_enabled=True,
            at_rest_encryption_enabled=True,
        )

        mock_client.create_api_cache.assert_called_once_with(
            apiId='test-api-id',
            ttl=600,
            apiCachingBehavior='PER_RESOLVER_CACHING',
            type='MEDIUM',
            transitEncryptionEnabled=True,
            atRestEncryptionEnabled=True,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_api_cache_with_health_metrics():
    """Test create_api_cache tool with health metrics configuration."""
    mock_client = MagicMock()
    mock_response = {
        'apiCache': {
            'ttl': 1800,
            'apiCachingBehavior': 'FULL_REQUEST_CACHING',
            'type': 'LARGE',
            'status': 'CREATING',
            'healthMetricsConfig': 'ENABLED',
        }
    }
    mock_client.create_api_cache.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_api_cache.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_api_cache_operation(
            api_id='test-api-id',
            ttl=1800,
            api_caching_behavior='FULL_REQUEST_CACHING',
            type='LARGE',
            health_metrics_config='ENABLED',
        )

        mock_client.create_api_cache.assert_called_once_with(
            apiId='test-api-id',
            ttl=1800,
            apiCachingBehavior='FULL_REQUEST_CACHING',
            type='LARGE',
            healthMetricsConfig='ENABLED',
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_api_cache_full():
    """Test create_api_cache tool with all parameters."""
    mock_client = MagicMock()
    mock_response = {
        'apiCache': {
            'ttl': 3600,
            'apiCachingBehavior': 'PER_RESOLVER_CACHING',
            'type': 'XLARGE',
            'status': 'CREATING',
            'transitEncryptionEnabled': True,
            'atRestEncryptionEnabled': True,
            'healthMetricsConfig': 'ENABLED',
        }
    }
    mock_client.create_api_cache.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_api_cache.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_api_cache_operation(
            api_id='test-api-id',
            ttl=3600,
            api_caching_behavior='PER_RESOLVER_CACHING',
            type='XLARGE',
            transit_encryption_enabled=True,
            at_rest_encryption_enabled=True,
            health_metrics_config='ENABLED',
        )

        mock_client.create_api_cache.assert_called_once_with(
            apiId='test-api-id',
            ttl=3600,
            apiCachingBehavior='PER_RESOLVER_CACHING',
            type='XLARGE',
            transitEncryptionEnabled=True,
            atRestEncryptionEnabled=True,
            healthMetricsConfig='ENABLED',
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_api_cache_with_disabled_encryption():
    """Test create_api_cache tool with encryption disabled."""
    mock_client = MagicMock()
    mock_response = {
        'apiCache': {
            'ttl': 900,
            'apiCachingBehavior': 'FULL_REQUEST_CACHING',
            'type': 'MEDIUM',
            'status': 'CREATING',
            'transitEncryptionEnabled': False,
            'atRestEncryptionEnabled': False,
        }
    }
    mock_client.create_api_cache.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_api_cache.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_api_cache_operation(
            api_id='test-api-id',
            ttl=900,
            api_caching_behavior='FULL_REQUEST_CACHING',
            type='MEDIUM',
            transit_encryption_enabled=False,
            at_rest_encryption_enabled=False,
        )

        mock_client.create_api_cache.assert_called_once_with(
            apiId='test-api-id',
            ttl=900,
            apiCachingBehavior='FULL_REQUEST_CACHING',
            type='MEDIUM',
            transitEncryptionEnabled=False,
            atRestEncryptionEnabled=False,
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_api_cache_with_disabled_health_metrics():
    """Test create_api_cache tool with health metrics disabled."""
    mock_client = MagicMock()
    mock_response = {
        'apiCache': {
            'ttl': 1200,
            'apiCachingBehavior': 'PER_RESOLVER_CACHING',
            'type': 'LARGE_2X',
            'status': 'CREATING',
            'healthMetricsConfig': 'DISABLED',
        }
    }
    mock_client.create_api_cache.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_api_cache.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_api_cache_operation(
            api_id='test-api-id',
            ttl=1200,
            api_caching_behavior='PER_RESOLVER_CACHING',
            type='LARGE_2X',
            health_metrics_config='DISABLED',
        )

        mock_client.create_api_cache.assert_called_once_with(
            apiId='test-api-id',
            ttl=1200,
            apiCachingBehavior='PER_RESOLVER_CACHING',
            type='LARGE_2X',
            healthMetricsConfig='DISABLED',
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_api_cache_empty_response():
    """Test create_api_cache tool with empty response from AWS."""
    mock_client = MagicMock()
    mock_response = {}
    mock_client.create_api_cache.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_api_cache.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_api_cache_operation(
            api_id='test-api-id',
            ttl=300,
            api_caching_behavior='FULL_REQUEST_CACHING',
            type='SMALL',
        )

        mock_client.create_api_cache.assert_called_once_with(
            apiId='test-api-id', ttl=300, apiCachingBehavior='FULL_REQUEST_CACHING', type='SMALL'
        )
        assert result == {'apiCache': {}}


@pytest.mark.asyncio
async def test_create_api_cache_large_instance():
    """Test create_api_cache tool with large instance type."""
    mock_client = MagicMock()
    mock_response = {
        'apiCache': {
            'ttl': 2400,
            'apiCachingBehavior': 'FULL_REQUEST_CACHING',
            'type': 'LARGE_12X',
            'status': 'CREATING',
            'transitEncryptionEnabled': True,
            'atRestEncryptionEnabled': True,
            'healthMetricsConfig': 'ENABLED',
        }
    }
    mock_client.create_api_cache.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_api_cache.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_api_cache_operation(
            api_id='test-api-id',
            ttl=2400,
            api_caching_behavior='FULL_REQUEST_CACHING',
            type='LARGE_12X',
            transit_encryption_enabled=True,
            at_rest_encryption_enabled=True,
            health_metrics_config='ENABLED',
        )

        mock_client.create_api_cache.assert_called_once_with(
            apiId='test-api-id',
            ttl=2400,
            apiCachingBehavior='FULL_REQUEST_CACHING',
            type='LARGE_12X',
            transitEncryptionEnabled=True,
            atRestEncryptionEnabled=True,
            healthMetricsConfig='ENABLED',
        )
        assert result == mock_response


def test_register_create_api_cache_tool():
    """Test that create_api_cache tool is registered correctly."""
    mock_mcp = MagicMock()
    register_create_api_cache_tool(mock_mcp)
    mock_mcp.tool.assert_called_once()


@pytest.mark.asyncio
async def test_create_api_cache_tool_execution():
    """Test create_api_cache tool execution through MCP."""
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

    register_create_api_cache_tool(mock_mcp)

    with patch(
        'awslabs.aws_appsync_mcp_server.tools.create_api_cache.create_api_cache_operation'
    ) as mock_op:
        mock_op.return_value = {'apiCache': {'status': 'CREATING'}}
        if captured_func is not None:
            result = await captured_func('test-api', 300, 'FULL_REQUEST_CACHING', 'SMALL')
            mock_op.assert_called_once_with(
                'test-api', 300, 'FULL_REQUEST_CACHING', 'SMALL', None, None, None
            )
            assert result == {'apiCache': {'status': 'CREATING'}}
