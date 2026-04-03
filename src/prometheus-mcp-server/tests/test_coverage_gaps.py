"""Tests to cover specific coverage gaps."""

import pytest
from awslabs.prometheus_mcp_server.server import PrometheusClient
from unittest.mock import AsyncMock, MagicMock, patch


class TestPrometheusClientSuccess:
    """Test successful PrometheusClient operations."""

    @pytest.mark.asyncio
    async def test_make_request_success_path(self):
        """Test successful request execution."""
        with (
            patch('boto3.Session') as mock_session,
            patch('requests.Session') as mock_req_session,
            patch('awslabs.prometheus_mcp_server.server.SigV4Auth'),
        ):
            # Mock session and credentials
            mock_creds = MagicMock()
            mock_session.return_value.get_credentials.return_value = mock_creds

            # Mock successful response
            mock_response = MagicMock()
            mock_response.json.return_value = {'status': 'success', 'data': {'result': []}}
            mock_req_session.return_value.__enter__.return_value.send.return_value = mock_response

            result = await PrometheusClient.make_request(
                prometheus_url='https://test.com', endpoint='query', params={'query': 'up'}
            )

            assert result == {'result': []}

    @pytest.mark.asyncio
    async def test_make_request_api_error(self):
        """Test API error response."""
        with (
            patch('boto3.Session') as mock_session,
            patch('requests.Session') as mock_req_session,
            patch('awslabs.prometheus_mcp_server.server.SigV4Auth'),
        ):
            mock_creds = MagicMock()
            mock_creds.access_key = 'test_key'
            mock_session.return_value.get_credentials.return_value = mock_creds

            # Mock API error response
            mock_response = MagicMock()
            mock_response.json.return_value = {'status': 'error', 'error': 'test error'}
            mock_req_session.return_value.__enter__.return_value.send.return_value = mock_response

            with pytest.raises(RuntimeError, match='Prometheus API request failed: test error'):
                await PrometheusClient.make_request(
                    prometheus_url='https://test.com', endpoint='query'
                )


class TestToolExceptionHandling:
    """Test exception handling in MCP tools."""

    @pytest.mark.asyncio
    async def test_list_metrics_exception(self):
        """Test list_metrics exception handling."""
        from awslabs.prometheus_mcp_server.server import list_metrics

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.prometheus_mcp_server.server.configure_workspace_for_request',
            side_effect=Exception('Test error'),
        ):
            with pytest.raises(Exception, match='Test error'):
                await list_metrics(mock_ctx)

            mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_server_info_exception(self):
        """Test get_server_info exception handling."""
        from awslabs.prometheus_mcp_server.server import get_server_info

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.prometheus_mcp_server.server.configure_workspace_for_request',
            side_effect=Exception('Test error'),
        ):
            with pytest.raises(Exception, match='Test error'):
                await get_server_info(mock_ctx)

            mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_available_workspaces_exception(self):
        """Test get_available_workspaces exception handling."""
        from awslabs.prometheus_mcp_server.server import get_available_workspaces

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.prometheus_mcp_server.server.get_prometheus_client',
            side_effect=Exception('Test error'),
        ):
            with pytest.raises(Exception, match='Test error'):
                await get_available_workspaces(mock_ctx)

            mock_ctx.error.assert_called_once()


class TestMainExecution:
    """Test main function execution."""

    def test_main_execution(self):
        """Test main function is callable."""
        from awslabs.prometheus_mcp_server.server import main

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.ConfigManager.parse_arguments'
            ) as mock_args,
            patch(
                'awslabs.prometheus_mcp_server.server.AWSCredentials.validate', return_value=False
            ),
            patch('sys.exit') as mock_exit,
        ):
            mock_args.return_value = MagicMock(url=None, region=None, profile=None, debug=False)

            main()
            assert mock_exit.called
