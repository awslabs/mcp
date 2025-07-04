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

"""Tests for Prometheus connection functionality."""

import pytest
import requests
from botocore.exceptions import ClientError
from unittest.mock import patch


@pytest.mark.asyncio
async def test_test_prometheus_connection_success():
    """Test successful connection to Prometheus."""
    with patch('awslabs.prometheus_mcp_server.server.make_prometheus_request') as mock_request:
        from awslabs.prometheus_mcp_server.server import test_prometheus_connection

        # Setup
        mock_request.return_value = ['metric1', 'metric2']

        # Execute
        result = await test_prometheus_connection()

        # Assert
        assert result is True
        mock_request.assert_called_once_with('label/__name__/values', params={})


@pytest.mark.asyncio
async def test_test_prometheus_connection_access_denied():
    """Test connection with access denied error."""
    with (
        patch('awslabs.prometheus_mcp_server.server.make_prometheus_request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
    ):
        from awslabs.prometheus_mcp_server.server import test_prometheus_connection

        # Setup
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access Denied'}}
        mock_request.side_effect = ClientError(error_response, 'GetLabels')

        # Execute
        result = await test_prometheus_connection()

        # Assert
        assert result is False
        mock_logger.error.assert_called()
        assert any('Access denied' in str(args) for args in mock_logger.error.call_args_list)


@pytest.mark.asyncio
async def test_test_prometheus_connection_resource_not_found():
    """Test connection with resource not found error."""
    with (
        patch('awslabs.prometheus_mcp_server.server.make_prometheus_request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
    ):
        from awslabs.prometheus_mcp_server.server import test_prometheus_connection

        # Setup
        error_response = {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not Found'}}
        mock_request.side_effect = ClientError(error_response, 'GetLabels')
        mock_config.prometheus_url = 'https://test-prometheus.amazonaws.com'

        # Execute
        result = await test_prometheus_connection()

        # Assert
        assert result is False
        mock_logger.error.assert_called()
        assert any('workspace not found' in str(args) for args in mock_logger.error.call_args_list)


@pytest.mark.asyncio
async def test_test_prometheus_connection_other_aws_error():
    """Test connection with other AWS API error."""
    with (
        patch('awslabs.prometheus_mcp_server.server.make_prometheus_request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
    ):
        from awslabs.prometheus_mcp_server.server import test_prometheus_connection

        # Setup
        error_response = {'Error': {'Code': 'InternalServerError', 'Message': 'Server Error'}}
        mock_request.side_effect = ClientError(error_response, 'GetLabels')

        # Execute
        result = await test_prometheus_connection()

        # Assert
        assert result is False
        mock_logger.error.assert_called()
        assert any('AWS API error' in str(args) for args in mock_logger.error.call_args_list)


@pytest.mark.asyncio
async def test_test_prometheus_connection_network_error():
    """Test connection with network error."""
    with (
        patch('awslabs.prometheus_mcp_server.server.make_prometheus_request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
    ):
        from awslabs.prometheus_mcp_server.server import test_prometheus_connection

        # Setup
        mock_request.side_effect = requests.RequestException('Connection refused')

        # Execute
        result = await test_prometheus_connection()

        # Assert
        assert result is False
        mock_logger.error.assert_called()
        assert any('Network error' in str(args) for args in mock_logger.error.call_args_list)


@pytest.mark.asyncio
async def test_test_prometheus_connection_generic_error():
    """Test connection with generic error."""
    with (
        patch('awslabs.prometheus_mcp_server.server.make_prometheus_request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
    ):
        from awslabs.prometheus_mcp_server.server import test_prometheus_connection

        # Setup
        mock_request.side_effect = Exception('Unexpected error')

        # Execute
        result = await test_prometheus_connection()

        # Assert
        assert result is False
        mock_logger.error.assert_called()
        assert any(
            'Error connecting to Prometheus' in str(args)
            for args in mock_logger.error.call_args_list
        )
