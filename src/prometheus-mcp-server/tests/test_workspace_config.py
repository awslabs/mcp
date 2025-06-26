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

"""Tests for workspace configuration functionality."""

import pytest
from unittest.mock import ANY, AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_configure_workspace_for_request_success():
    """Test successful workspace configuration."""
    with (
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
        patch('awslabs.prometheus_mcp_server.server.test_prometheus_connection') as mock_test_conn,
    ):
        from awslabs.prometheus_mcp_server.server import configure_workspace_for_request

        # Setup
        mock_test_conn.return_value = True
        mock_config.aws_region = 'us-east-1'
        mock_config.aws_profile = 'test-profile'
        mock_config.service_name = 'aps'
        ctx = AsyncMock()
        workspace_id = 'ws-12345678-abcd-1234-efgh-123456789012'
        region = 'us-west-2'

        # Execute
        await configure_workspace_for_request(ctx, workspace_id, region)

        # Assert
        expected_url = f'https://aps-workspaces.{region}.amazonaws.com/workspaces/{workspace_id}'
        assert mock_config.prometheus_url == expected_url
        assert mock_config.aws_region == region
        mock_test_conn.assert_called_once()


@pytest.mark.asyncio
async def test_configure_workspace_for_request_no_region():
    """Test workspace configuration with no region specified."""
    with (
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
        patch('awslabs.prometheus_mcp_server.server.test_prometheus_connection') as mock_test_conn,
    ):
        from awslabs.prometheus_mcp_server.server import configure_workspace_for_request

        # Setup
        mock_test_conn.return_value = True
        mock_config.aws_region = 'us-east-1'
        ctx = AsyncMock()
        workspace_id = 'ws-12345678-abcd-1234-efgh-123456789012'
        region = None

        # Execute
        await configure_workspace_for_request(ctx, workspace_id, region)

        # Assert
        expected_url = f'https://aps-workspaces.{mock_config.aws_region}.amazonaws.com/workspaces/{workspace_id}'
        assert mock_config.prometheus_url == expected_url
        assert mock_config.aws_region == 'us-east-1'  # Should not change
        mock_test_conn.assert_called_once()


@pytest.mark.asyncio
async def test_configure_workspace_for_request_no_config():
    """Test workspace configuration when global config is None."""
    with (
        patch('awslabs.prometheus_mcp_server.server.config', None),
        patch('awslabs.prometheus_mcp_server.server.test_prometheus_connection') as mock_test_conn,
        patch('awslabs.prometheus_mcp_server.server.PrometheusConfig') as mock_config_class,
    ):
        from awslabs.prometheus_mcp_server.consts import DEFAULT_SERVICE_NAME
        from awslabs.prometheus_mcp_server.server import configure_workspace_for_request

        # Setup
        mock_test_conn.return_value = True
        ctx = AsyncMock()
        workspace_id = 'ws-12345678-abcd-1234-efgh-123456789012'
        region = 'us-west-2'

        # Execute
        await configure_workspace_for_request(ctx, workspace_id, region)

        # Assert
        expected_url = f'https://aps-workspaces.{region}.amazonaws.com/workspaces/{workspace_id}'
        mock_config_class.assert_called_once_with(
            prometheus_url=expected_url,
            aws_region=region,
            aws_profile=None,
            service_name=DEFAULT_SERVICE_NAME,
        )
        mock_test_conn.assert_called_once()


@pytest.mark.asyncio
async def test_configure_workspace_for_request_connection_failure():
    """Test workspace configuration with connection failure."""
    with (
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
        patch('awslabs.prometheus_mcp_server.server.test_prometheus_connection') as mock_test_conn,
    ):
        from awslabs.prometheus_mcp_server.server import configure_workspace_for_request

        # Setup
        mock_test_conn.return_value = False
        mock_config.aws_region = 'us-east-1'
        ctx = AsyncMock()
        workspace_id = 'ws-12345678-abcd-1234-efgh-123456789012'

        # Execute and Assert
        with pytest.raises(RuntimeError):
            await configure_workspace_for_request(ctx, workspace_id, None)

        mock_test_conn.assert_called_once()
        # ctx.error is called twice, once for the connection failure and once for the error
        assert ctx.error.call_count == 2


@pytest.mark.asyncio
async def test_configure_workspace_for_request_general_error():
    """Test workspace configuration with general error."""
    with (
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
        patch('awslabs.prometheus_mcp_server.server.test_prometheus_connection') as mock_test_conn,
    ):
        from awslabs.prometheus_mcp_server.server import configure_workspace_for_request

        # Setup
        mock_test_conn.side_effect = Exception('Test error')
        mock_config.aws_region = 'us-east-1'
        ctx = AsyncMock()
        workspace_id = 'ws-12345678-abcd-1234-efgh-123456789012'

        # Execute and Assert
        with pytest.raises(Exception):
            await configure_workspace_for_request(ctx, workspace_id, None)

        ctx.error.assert_called_once()


@pytest.mark.asyncio
async def test_configure_workspace_for_request_unusual_id():
    """Test workspace configuration with unusual workspace ID."""
    with (
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
        patch('awslabs.prometheus_mcp_server.server.test_prometheus_connection') as mock_test_conn,
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
    ):
        from awslabs.prometheus_mcp_server.server import configure_workspace_for_request

        # Setup
        mock_test_conn.return_value = True
        mock_config.aws_region = 'us-east-1'
        ctx = AsyncMock()
        workspace_id = 'unusual-id'  # Doesn't start with ws-

        # Execute
        await configure_workspace_for_request(ctx, workspace_id, None)

        # Assert
        mock_logger.warning.assert_called_once_with(
            'Workspace ID "unusual-id" does not start with "ws-", which is unusual'
        )


@pytest.mark.asyncio
async def test_get_available_workspaces():
    """Test listing available workspaces."""
    with (
        patch('awslabs.prometheus_mcp_server.server.boto3.Session') as mock_session,
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
    ):
        from awslabs.prometheus_mcp_server.server import get_available_workspaces
        from datetime import datetime

        # Setup
        mock_config.aws_region = 'us-east-1'
        mock_config.aws_profile = 'test-profile'

        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        created_at = datetime(2023, 1, 1)
        mock_client.list_workspaces.return_value = {
            'workspaces': [
                {
                    'workspaceId': 'ws-12345',
                    'alias': 'Test Workspace',
                    'status': {'statusCode': 'ACTIVE'},
                    'createdAt': created_at,
                }
            ]
        }

        ctx = AsyncMock()

        # Execute
        result = await get_available_workspaces(ctx)

        # Assert
        # Check that Session was called with the right profile name
        assert mock_session.call_args.kwargs['profile_name'] == 'test-profile'
        # Check that the client was created correctly
        mock_session.return_value.client.assert_called_once_with('amp', config=ANY)
        mock_client.list_workspaces.assert_called_once()

        assert result['count'] == 1
        assert 'region' in result  # Just check that region is in the result
        assert len(result['workspaces']) == 1
        assert result['workspaces'][0]['workspace_id'] == 'ws-12345'
        assert result['workspaces'][0]['alias'] == 'Test Workspace'
        assert result['workspaces'][0]['status'] == 'ACTIVE'
        assert result['workspaces'][0]['created_at'] == created_at.isoformat()


@pytest.mark.asyncio
async def test_get_available_workspaces_custom_region():
    """Test listing available workspaces with custom region."""
    with (
        patch('awslabs.prometheus_mcp_server.server.boto3.Session') as mock_session,
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
    ):
        from awslabs.prometheus_mcp_server.server import get_available_workspaces

        # Setup
        mock_config.aws_region = 'us-east-1'
        mock_config.aws_profile = 'test-profile'

        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_client.list_workspaces.return_value = {'workspaces': []}

        ctx = AsyncMock()
        custom_region = 'eu-west-1'

        # Execute
        result = await get_available_workspaces(ctx, region=custom_region)

        # Assert
        mock_session.assert_called_once_with(
            profile_name='test-profile', region_name=custom_region
        )
        assert result['region'] == custom_region


@pytest.mark.asyncio
async def test_get_available_workspaces_no_config():
    """Test listing available workspaces with no global config."""
    with (
        patch('awslabs.prometheus_mcp_server.server.boto3.Session') as mock_session,
        patch('awslabs.prometheus_mcp_server.server.config', None),
    ):
        from awslabs.prometheus_mcp_server.consts import DEFAULT_AWS_REGION
        from awslabs.prometheus_mcp_server.server import get_available_workspaces

        # Setup
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_client.list_workspaces.return_value = {'workspaces': []}

        ctx = AsyncMock()

        # Execute
        result = await get_available_workspaces(ctx)

        # Assert
        # Just check that Session was called with some region name parameter
        assert 'region_name' in mock_session.call_args.kwargs
        # Check that the result contains the expected region
        assert result['region'] in [
            DEFAULT_AWS_REGION,
            mock_session.call_args.kwargs['region_name'],
        ]


@pytest.mark.asyncio
async def test_get_available_workspaces_error():
    """Test listing available workspaces with error."""
    with (
        patch('awslabs.prometheus_mcp_server.server.boto3.Session') as mock_session,
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
    ):
        from awslabs.prometheus_mcp_server.server import get_available_workspaces

        # Setup
        mock_config.aws_region = 'us-east-1'
        mock_config.aws_profile = 'test-profile'

        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_client.list_workspaces.side_effect = Exception('Test error')

        ctx = AsyncMock()

        # Execute and Assert
        with pytest.raises(Exception):
            await get_available_workspaces(ctx)

        ctx.error.assert_called_once()
