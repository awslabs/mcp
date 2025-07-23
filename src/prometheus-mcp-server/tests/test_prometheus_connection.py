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

"""Tests for the PrometheusConnection class."""

import pytest
import requests
from awslabs.prometheus_mcp_server.server import PrometheusConnection
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, patch


class TestPrometheusConnection:
    """Tests for the PrometheusConnection class."""

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test that test_connection returns True when connection is successful."""
        mock_make_request = AsyncMock()
        mock_make_request.return_value = {'values': ['metric1', 'metric2']}

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.PrometheusClient.make_request',
                mock_make_request,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            result = await PrometheusConnection.test_connection(
                prometheus_url='https://example.com', region='us-east-1', profile='test-profile'
            )

            assert result is True
            mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_access_denied(self):
        """Test that test_connection returns False when access is denied."""
        error_response = {'Error': {'Code': 'AccessDeniedException'}}
        mock_make_request = AsyncMock(side_effect=ClientError(error_response, 'GetLabels'))

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.PrometheusClient.make_request',
                mock_make_request,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            result = await PrometheusConnection.test_connection(
                prometheus_url='https://example.com', region='us-east-1', profile='test-profile'
            )

            assert result is False
            mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_resource_not_found(self):
        """Test that test_connection returns False when resource is not found."""
        error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
        mock_make_request = AsyncMock(side_effect=ClientError(error_response, 'GetLabels'))

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.PrometheusClient.make_request',
                mock_make_request,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            result = await PrometheusConnection.test_connection(
                prometheus_url='https://example.com', region='us-east-1', profile='test-profile'
            )

            assert result is False
            mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_other_aws_error(self):
        """Test that test_connection returns False when other AWS error occurs."""
        error_response = {'Error': {'Code': 'InternalServerError'}}
        mock_make_request = AsyncMock(side_effect=ClientError(error_response, 'GetLabels'))

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.PrometheusClient.make_request',
                mock_make_request,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            result = await PrometheusConnection.test_connection(
                prometheus_url='https://example.com', region='us-east-1', profile='test-profile'
            )

            assert result is False
            mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_network_error(self):
        """Test that test_connection returns False when network error occurs."""
        mock_make_request = AsyncMock(side_effect=requests.RequestException('Network error'))

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.PrometheusClient.make_request',
                mock_make_request,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            result = await PrometheusConnection.test_connection(
                prometheus_url='https://example.com', region='us-east-1', profile='test-profile'
            )

            assert result is False
            mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_generic_error(self):
        """Test that test_connection returns False when generic error occurs."""
        mock_make_request = AsyncMock(side_effect=Exception('Generic error'))

        with (
            patch(
                'awslabs.prometheus_mcp_server.server.PrometheusClient.make_request',
                mock_make_request,
            ),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            result = await PrometheusConnection.test_connection(
                prometheus_url='https://example.com', region='us-east-1', profile='test-profile'
            )

            assert result is False
            mock_make_request.assert_called_once()
