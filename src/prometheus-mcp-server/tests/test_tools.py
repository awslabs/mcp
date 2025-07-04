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

"""Tests for the MCP tool functions."""

import os
import pytest
from awslabs.prometheus_mcp_server.server import (
    MetricsList,
    ServerInfo,
    execute_query,
    execute_range_query,
    get_available_workspaces,
    get_server_info,
    list_metrics,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestTools:
    """Tests for the MCP tool functions."""

    @pytest.mark.asyncio
    async def test_execute_query(self, mock_context):
        """Test that execute_query correctly executes a query."""
        mock_configure = AsyncMock(
            return_value={
                'prometheus_url': 'https://example.com',
                'region': 'us-east-1',
                'profile': 'test-profile',
                'workspace_id': 'ws-12345',
            }
        )
        mock_make_request = AsyncMock(return_value={'resultType': 'vector', 'result': []})
        mock_validate = MagicMock(return_value=True)

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.configure_workspace_for_request',
                mock_configure,
            ),
            patch(
                'awslabs.prometheus_mcp_server.server.PrometheusClient.make_request',
                mock_make_request,
            ),
            patch(
                'awslabs.prometheus_mcp_server.server.SecurityValidator.validate_query',
                mock_validate,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            result = await execute_query(
                ctx=mock_context,
                workspace_id='ws-12345',
                query='up',
                time='2023-01-01T00:00:00Z',
                region='us-east-1',
                profile='test-profile',
            )

            assert result == {'resultType': 'vector', 'result': []}
            mock_configure.assert_called_once_with(
                mock_context, 'ws-12345', 'us-east-1', 'test-profile'
            )
            mock_validate.assert_called_once_with('up')
            mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_query_validation_failure(self, mock_context):
        """Test that execute_query raises ValueError when query validation fails."""
        mock_configure = AsyncMock(
            return_value={
                'prometheus_url': 'https://example.com',
                'region': 'us-east-1',
                'profile': 'test-profile',
                'workspace_id': 'ws-12345',
            }
        )
        mock_validate = MagicMock(return_value=False)

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.configure_workspace_for_request',
                mock_configure,
            ),
            patch(
                'awslabs.prometheus_mcp_server.server.SecurityValidator.validate_query',
                mock_validate,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            with pytest.raises(ValueError, match='Query validation failed'):
                await execute_query(
                    ctx=mock_context,
                    workspace_id='ws-12345',
                    query='dangerous;query',
                    region='us-east-1',
                    profile='test-profile',
                )

    @pytest.mark.asyncio
    async def test_execute_query_with_error(self, mock_context):
        """Test that execute_query handles errors correctly."""
        mock_configure = AsyncMock(
            return_value={
                'prometheus_url': 'https://example.com',
                'region': 'us-east-1',
                'profile': 'test-profile',
                'workspace_id': 'ws-12345',
            }
        )
        mock_validate = MagicMock(return_value=True)
        mock_make_request = AsyncMock(side_effect=Exception('Test error'))

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.configure_workspace_for_request',
                mock_configure,
            ),
            patch(
                'awslabs.prometheus_mcp_server.server.PrometheusClient.make_request',
                mock_make_request,
            ),
            patch(
                'awslabs.prometheus_mcp_server.server.SecurityValidator.validate_query',
                mock_validate,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            with pytest.raises(Exception, match='Test error'):
                await execute_query(
                    ctx=mock_context,
                    workspace_id='ws-12345',
                    query='up',
                    region='us-east-1',
                    profile='test-profile',
                )

            mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_range_query(self, mock_context):
        """Test that execute_range_query correctly executes a range query."""
        mock_configure = AsyncMock(
            return_value={
                'prometheus_url': 'https://example.com',
                'region': 'us-east-1',
                'profile': 'test-profile',
                'workspace_id': 'ws-12345',
            }
        )
        mock_make_request = AsyncMock(return_value={'resultType': 'matrix', 'result': []})
        mock_validate = MagicMock(return_value=True)

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.configure_workspace_for_request',
                mock_configure,
            ),
            patch(
                'awslabs.prometheus_mcp_server.server.PrometheusClient.make_request',
                mock_make_request,
            ),
            patch(
                'awslabs.prometheus_mcp_server.server.SecurityValidator.validate_query',
                mock_validate,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            result = await execute_range_query(
                ctx=mock_context,
                workspace_id='ws-12345',
                query='rate(http_requests_total[5m])',
                start='2023-01-01T00:00:00Z',
                end='2023-01-01T01:00:00Z',
                step='5m',
                region='us-east-1',
                profile='test-profile',
            )

            assert result == {'resultType': 'matrix', 'result': []}
            mock_configure.assert_called_once_with(
                mock_context, 'ws-12345', 'us-east-1', 'test-profile'
            )
            mock_validate.assert_called_once_with('rate(http_requests_total[5m])')
            mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_metrics(self, mock_context):
        """Test that list_metrics correctly lists metrics."""
        mock_configure = AsyncMock(
            return_value={
                'prometheus_url': 'https://example.com',
                'region': 'us-east-1',
                'profile': 'test-profile',
                'workspace_id': 'ws-12345',
            }
        )
        mock_make_request = AsyncMock(return_value=['metric1', 'metric2', 'metric3'])

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.configure_workspace_for_request',
                mock_configure,
            ),
            patch(
                'awslabs.prometheus_mcp_server.server.PrometheusClient.make_request',
                mock_make_request,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            result = await list_metrics(
                ctx=mock_context,
                workspace_id='ws-12345',
                region='us-east-1',
                profile='test-profile',
            )

            assert isinstance(result, MetricsList)
            assert result.metrics == ['metric1', 'metric2', 'metric3']
            mock_configure.assert_called_once_with(
                mock_context, 'ws-12345', 'us-east-1', 'test-profile'
            )
            mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_server_info(self, mock_context):
        """Test that get_server_info correctly returns server information."""
        mock_configure = AsyncMock(
            return_value={
                'prometheus_url': 'https://example.com',
                'region': 'us-east-1',
                'profile': 'test-profile',
                'workspace_id': 'ws-12345',
            }
        )

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.configure_workspace_for_request',
                mock_configure,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            result = await get_server_info(
                ctx=mock_context,
                workspace_id='ws-12345',
                region='us-east-1',
                profile='test-profile',
            )

            assert isinstance(result, ServerInfo)
            assert result.prometheus_url == 'https://example.com'
            assert result.aws_region == 'us-east-1'
            assert result.aws_profile == 'test-profile'
            assert result.service_name == 'aps'
            mock_configure.assert_called_once_with(
                mock_context, 'ws-12345', 'us-east-1', 'test-profile'
            )

    @pytest.mark.asyncio
    async def test_get_available_workspaces(self, mock_context):
        """Test that get_available_workspaces correctly lists available workspaces."""
        mock_client = MagicMock()
        mock_client.list_workspaces.return_value = {
            'workspaces': [
                {
                    'workspaceId': 'ws-12345',
                    'alias': 'workspace1',
                    'status': {'statusCode': 'ACTIVE'},
                },
                {
                    'workspaceId': 'ws-67890',
                    'alias': 'workspace2',
                    'status': {'statusCode': 'ACTIVE'},
                },
            ]
        }

        mock_get_workspace_details = AsyncMock(
            side_effect=[
                {
                    'workspace_id': 'ws-12345',
                    'alias': 'workspace1',
                    'status': 'ACTIVE',
                    'prometheus_url': 'https://example.com/workspaces/ws-12345',
                    'region': 'us-east-1',
                },
                {
                    'workspace_id': 'ws-67890',
                    'alias': 'workspace2',
                    'status': 'ACTIVE',
                    'prometheus_url': 'https://example.com/workspaces/ws-67890',
                    'region': 'us-east-1',
                },
            ]
        )

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.get_prometheus_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.prometheus_mcp_server.server.get_workspace_details',
                mock_get_workspace_details,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
            patch.dict(os.environ, {'AWS_REGION': '', 'AWS_PROFILE': ''}, clear=True),
        ):
            result = await get_available_workspaces(
                ctx=mock_context, region='us-east-1', profile='test-profile'
            )

            assert result['count'] == 2
            assert result['region'] == 'us-east-1'
            assert result['requires_user_selection'] is True
            assert len(result['workspaces']) == 2
            assert result['workspaces'][0]['workspace_id'] == 'ws-12345'
            assert result['workspaces'][1]['workspace_id'] == 'ws-67890'
            mock_client.list_workspaces.assert_called_once()
            assert mock_get_workspace_details.call_count == 2

    @pytest.mark.asyncio
    async def test_get_available_workspaces_with_inactive(self, mock_context):
        """Test that get_available_workspaces correctly handles inactive workspaces."""
        mock_client = MagicMock()
        mock_client.list_workspaces.return_value = {
            'workspaces': [
                {
                    'workspaceId': 'ws-12345',
                    'alias': 'workspace1',
                    'status': {'statusCode': 'ACTIVE'},
                },
                {
                    'workspaceId': 'ws-67890',
                    'alias': 'workspace2',
                    'status': {'statusCode': 'CREATING'},
                },
            ]
        }

        mock_get_workspace_details = AsyncMock(
            return_value={
                'workspace_id': 'ws-12345',
                'alias': 'workspace1',
                'status': 'ACTIVE',
                'prometheus_url': 'https://example.com/workspaces/ws-12345',
                'region': 'us-east-1',
            }
        )

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.get_prometheus_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.prometheus_mcp_server.server.get_workspace_details',
                mock_get_workspace_details,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
            patch.dict(os.environ, {'AWS_REGION': '', 'AWS_PROFILE': ''}, clear=True),
        ):
            result = await get_available_workspaces(
                ctx=mock_context, region='us-east-1', profile='test-profile'
            )

            assert result['count'] == 2
            assert result['region'] == 'us-east-1'
            # With our new implementation, we always require user selection when multiple workspaces exist
            assert result['requires_user_selection'] is True
            assert len(result['workspaces']) == 2
            assert result['workspaces'][0]['workspace_id'] == 'ws-12345'
            assert result['workspaces'][0]['status'] == 'ACTIVE'
            assert 'prometheus_url' in result['workspaces'][0]
            assert result['workspaces'][1]['workspace_id'] == 'ws-67890'
            assert result['workspaces'][1]['status'] == 'CREATING'
            assert 'prometheus_url' not in result['workspaces'][1]
            mock_client.list_workspaces.assert_called_once()
            mock_get_workspace_details.assert_called_once_with(
                'ws-12345', 'us-east-1', 'test-profile'
            )

    @pytest.mark.asyncio
    async def test_get_available_workspaces_with_error(self, mock_context):
        """Test that get_available_workspaces handles errors when getting workspace details."""
        mock_client = MagicMock()
        mock_client.list_workspaces.return_value = {
            'workspaces': [
                {
                    'workspaceId': 'ws-12345',
                    'alias': 'workspace1',
                    'status': {'statusCode': 'ACTIVE'},
                },
                {
                    'workspaceId': 'ws-67890',
                    'alias': 'workspace2',
                    'status': {'statusCode': 'ACTIVE'},
                },
            ]
        }

        # First call succeeds, second call fails
        mock_get_workspace_details = AsyncMock(
            side_effect=[
                {
                    'workspace_id': 'ws-12345',
                    'alias': 'workspace1',
                    'status': 'ACTIVE',
                    'prometheus_url': 'https://example.com/workspaces/ws-12345',
                    'region': 'us-east-1',
                },
                Exception('Failed to get workspace details'),
            ]
        )

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.get_prometheus_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.prometheus_mcp_server.server.get_workspace_details',
                mock_get_workspace_details,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
            patch.dict(os.environ, {'AWS_REGION': '', 'AWS_PROFILE': ''}, clear=True),
        ):
            result = await get_available_workspaces(
                ctx=mock_context, region='us-east-1', profile='test-profile'
            )

            assert result['count'] == 1  # Only one workspace successfully retrieved
            assert result['region'] == 'us-east-1'
            assert result['requires_user_selection'] is False
            assert len(result['workspaces']) == 1
            assert result['workspaces'][0]['workspace_id'] == 'ws-12345'
            mock_client.list_workspaces.assert_called_once()
            assert mock_get_workspace_details.call_count == 2

    @pytest.mark.asyncio
    async def test_get_available_workspaces_with_configured_workspace_id(self, mock_context):
        """Test that get_available_workspaces correctly handles a configured workspace ID from URL."""
        mock_client = MagicMock()
        mock_client.list_workspaces.return_value = {
            'workspaces': [
                {
                    'workspaceId': 'ws-12345',
                    'alias': 'workspace1',
                    'status': {'statusCode': 'ACTIVE'},
                },
                {
                    'workspaceId': 'ws-67890',
                    'alias': 'workspace2',
                    'status': {'statusCode': 'ACTIVE'},
                },
            ]
        }

        mock_get_workspace_details = AsyncMock(
            side_effect=[
                {
                    'workspace_id': 'ws-12345',
                    'alias': 'workspace1',
                    'status': 'ACTIVE',
                    'prometheus_url': 'https://example.com/workspaces/ws-12345',
                    'region': 'us-east-1',
                },
                {
                    'workspace_id': 'ws-67890',
                    'alias': 'workspace2',
                    'status': 'ACTIVE',
                    'prometheus_url': 'https://example.com/workspaces/ws-67890',
                    'region': 'us-east-1',
                },
            ]
        )

        # Set environment variable with URL containing workspace ID
        os.environ['PROMETHEUS_URL'] = 'https://example.com/workspaces/ws-12345'

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.get_prometheus_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.prometheus_mcp_server.server.get_workspace_details',
                mock_get_workspace_details,
            ),
            patch(
                'awslabs.prometheus_mcp_server.server.extract_workspace_id_from_url',
                return_value='ws-12345',
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            result = await get_available_workspaces(
                ctx=mock_context, region='us-east-1', profile='test-profile'
            )

            assert result['count'] == 2
            assert result['region'] == 'us-east-1'
            assert (
                result['requires_user_selection'] is False
            )  # Should be False because we have a configured workspace
            assert result['configured_workspace_id'] == 'ws-12345'
            assert len(result['workspaces']) == 2
            # The configured workspace should be first in the list
            assert result['workspaces'][0]['workspace_id'] == 'ws-12345'
            assert result['workspaces'][0]['is_configured'] is True
            assert result['workspaces'][1]['workspace_id'] == 'ws-67890'
            assert result['workspaces'][1]['is_configured'] is False

        # Reset environment variable
        del os.environ['PROMETHEUS_URL']

    @pytest.mark.asyncio
    async def test_get_available_workspaces_with_configured_workspace_id_not_in_list(
        self, mock_context
    ):
        """Test that get_available_workspaces correctly handles a configured workspace ID that's not in the list."""
        mock_client = MagicMock()
        mock_client.list_workspaces.return_value = {
            'workspaces': [
                {
                    'workspaceId': 'ws-67890',
                    'alias': 'workspace2',
                    'status': {'statusCode': 'ACTIVE'},
                }
            ]
        }

        mock_get_workspace_details = AsyncMock(
            return_value={
                'workspace_id': 'ws-67890',
                'alias': 'workspace2',
                'status': 'ACTIVE',
                'prometheus_url': 'https://example.com/workspaces/ws-67890',
                'region': 'us-east-1',
            }
        )

        # Set environment variable with URL containing workspace ID that's not in the list
        os.environ['PROMETHEUS_URL'] = 'https://example.com/workspaces/ws-12345'

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.get_prometheus_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.prometheus_mcp_server.server.get_workspace_details',
                mock_get_workspace_details,
            ),
            patch(
                'awslabs.prometheus_mcp_server.server.extract_workspace_id_from_url',
                return_value='ws-12345',
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            result = await get_available_workspaces(
                ctx=mock_context, region='us-east-1', profile='test-profile'
            )

            assert (
                result['count'] == 2
            )  # Should include both the configured workspace and the one from the list
            assert result['region'] == 'us-east-1'
            assert (
                result['requires_user_selection'] is False
            )  # Should be False because we have a configured workspace
            assert result['configured_workspace_id'] == 'ws-12345'
            assert len(result['workspaces']) == 2
            # The configured workspace should be first in the list, even though it wasn't in the original list
            assert result['workspaces'][0]['workspace_id'] == 'ws-12345'
            assert result['workspaces'][0]['is_configured'] is True
            assert (
                'note' in result['workspaces'][0]
            )  # Should have a note about being detected from URL
            assert result['workspaces'][1]['workspace_id'] == 'ws-67890'
            assert result['workspaces'][1]['is_configured'] is False

        # Reset environment variable
        del os.environ['PROMETHEUS_URL']

    def test_extract_workspace_id_from_url(self):
        """Test that extract_workspace_id_from_url correctly extracts workspace IDs from URLs."""
        from awslabs.prometheus_mcp_server.server import extract_workspace_id_from_url

        # Test with valid URLs
        valid_urls = [
            ('https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-12345', 'ws-12345'),
            ('https://example.com/workspaces/ws-abcde-12345-xyz', 'ws-abcde-12345-xyz'),
            ('http://localhost:9090/workspaces/ws-test', 'ws-test'),
            (
                'https://aps-workspaces.region.amazonaws.com/workspaces/ws-12345/api/v1/query',
                'ws-12345',
            ),
            # Additional test cases
            (
                'https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-12345/api/v1',
                'ws-12345',
            ),
            ('https://example.com/workspaces/ws-12345?param=value', 'ws-12345'),
            ('https://example.com/workspaces/ws-12345#fragment', 'ws-12345'),
        ]

        for url, expected_id in valid_urls:
            assert extract_workspace_id_from_url(url) == expected_id

        # Test with invalid URLs
        invalid_urls = [
            None,
            '',
            'https://example.com',
            'https://example.com/workspace/ws-12345',  # wrong path segment
            'https://example.com/workspaces/not-a-workspace-id',
            'https://example.com/workspaces/',  # missing workspace ID
            'https://example.com/workspaces',  # missing trailing slash
        ]

        for url in invalid_urls:
            assert extract_workspace_id_from_url(url) is None
