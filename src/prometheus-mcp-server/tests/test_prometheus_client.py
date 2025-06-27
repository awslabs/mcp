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

"""Tests for the PrometheusClient class."""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, ANY
import requests
from botocore.exceptions import ClientError
from awslabs.prometheus_mcp_server.server import PrometheusClient


class TestPrometheusClient:
    """Tests for the PrometheusClient class."""

    @pytest.mark.asyncio
    async def test_make_request_success(self):
        """Test that make_request successfully makes a request and returns data."""
        # Mock the boto3 session and credentials
        mock_session = MagicMock()
        mock_credentials = MagicMock()
        mock_session.get_credentials.return_value = mock_credentials
        
        # Mock the requests session and response
        mock_req_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "data": {"resultType": "vector", "result": []}
        }
        mock_req_session.send.return_value = mock_response
        
        with patch("awslabs.prometheus_mcp_server.server.boto3.Session", return_value=mock_session), \
             patch("awslabs.prometheus_mcp_server.server.requests.Session", return_value=mock_req_session), \
             patch("awslabs.prometheus_mcp_server.server.requests.Request"), \
             patch("awslabs.prometheus_mcp_server.server.SigV4Auth"), \
             patch("awslabs.prometheus_mcp_server.server.AWSRequest"), \
             patch("awslabs.prometheus_mcp_server.server.logger"):
            
            result = await PrometheusClient.make_request(
                prometheus_url="https://example.com",
                endpoint="query",
                params={"query": "up"},
                region="us-east-1",
                profile="test-profile"
            )
            
            assert result == {"resultType": "vector", "result": []}
            mock_session.get_credentials.assert_called_once()
            mock_req_session.send.assert_called_once()
            mock_response.json.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_no_url(self):
        """Test that make_request raises ValueError when no URL is provided."""
        with pytest.raises(ValueError, match="Prometheus URL not configured"):
            await PrometheusClient.make_request(
                prometheus_url="",
                endpoint="query",
                params={"query": "up"}
            )

    @pytest.mark.asyncio
    async def test_make_request_invalid_endpoint_type(self):
        """Test that make_request raises ValueError when endpoint is not a string."""
        with pytest.raises(ValueError, match="Endpoint must be a string"):
            await PrometheusClient.make_request(
                prometheus_url="https://example.com",
                endpoint=123,
                params={"query": "up"}
            )

    @pytest.mark.asyncio
    async def test_make_request_dangerous_endpoint(self):
        """Test that make_request raises ValueError when endpoint contains dangerous characters."""
        with pytest.raises(ValueError, match="Invalid endpoint: potentially dangerous characters detected"):
            await PrometheusClient.make_request(
                prometheus_url="https://example.com",
                endpoint="query;rm -rf /",
                params={"query": "up"}
            )

    @pytest.mark.asyncio
    async def test_make_request_dangerous_params(self):
        """Test that make_request raises ValueError when params contain dangerous values."""
        with patch("awslabs.prometheus_mcp_server.server.SecurityValidator.validate_params", return_value=False):
            with pytest.raises(ValueError, match="Invalid parameters: potentially dangerous values detected"):
                await PrometheusClient.make_request(
                    prometheus_url="https://example.com",
                    endpoint="query",
                    params={"query": "dangerous;rm -rf /"}
                )

    @pytest.mark.asyncio
    async def test_make_request_api_url_construction(self):
        """Test that make_request correctly constructs the API URL."""
        # Mock the boto3 session and credentials
        mock_session = MagicMock()
        mock_credentials = MagicMock()
        mock_session.get_credentials.return_value = mock_credentials
        
        # Mock the requests session and response
        mock_req_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "data": {"resultType": "vector", "result": []}
        }
        mock_req_session.send.return_value = mock_response
        
        # Mock AWSRequest to capture the URL
        mock_aws_request = MagicMock()
        
        with patch("awslabs.prometheus_mcp_server.server.boto3.Session", return_value=mock_session), \
             patch("awslabs.prometheus_mcp_server.server.requests.Session", return_value=mock_req_session), \
             patch("awslabs.prometheus_mcp_server.server.requests.Request"), \
             patch("awslabs.prometheus_mcp_server.server.SigV4Auth"), \
             patch("awslabs.prometheus_mcp_server.server.AWSRequest", return_value=mock_aws_request), \
             patch("awslabs.prometheus_mcp_server.server.logger"):
            
            # Test with URL that doesn't end with /api/v1
            await PrometheusClient.make_request(
                prometheus_url="https://example.com",
                endpoint="query",
                params={"query": "up"}
            )
            
            # Check that the URL was constructed correctly
            assert mock_aws_request.method == "GET"
            assert "params" in mock_aws_request.kwargs
            
            # Test with URL that already ends with /api/v1
            mock_aws_request.reset_mock()
            await PrometheusClient.make_request(
                prometheus_url="https://example.com/api/v1",
                endpoint="query",
                params={"query": "up"}
            )
            
            # Check that the URL was constructed correctly
            assert mock_aws_request.method == "GET"
            assert "params" in mock_aws_request.kwargs

    @pytest.mark.asyncio
    async def test_make_request_api_error(self):
        """Test that make_request raises RuntimeError when the API returns an error status."""
        # Mock the boto3 session and credentials
        mock_session = MagicMock()
        mock_credentials = MagicMock()
        mock_session.get_credentials.return_value = mock_credentials
        
        # Mock the requests session and response
        mock_req_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "error",
            "error": "Query parsing error"
        }
        mock_req_session.send.return_value = mock_response
        
        with patch("awslabs.prometheus_mcp_server.server.boto3.Session", return_value=mock_session), \
             patch("awslabs.prometheus_mcp_server.server.requests.Session", return_value=mock_req_session), \
             patch("awslabs.prometheus_mcp_server.server.requests.Request"), \
             patch("awslabs.prometheus_mcp_server.server.SigV4Auth"), \
             patch("awslabs.prometheus_mcp_server.server.AWSRequest"), \
             patch("awslabs.prometheus_mcp_server.server.logger"):
            
            with pytest.raises(RuntimeError, match="Prometheus API request failed: Query parsing error"):
                await PrometheusClient.make_request(
                    prometheus_url="https://example.com",
                    endpoint="query",
                    params={"query": "invalid query"}
                )

    @pytest.mark.asyncio
    async def test_make_request_network_error_with_retry(self):
        """Test that make_request retries on network errors."""
        # Mock the boto3 session and credentials
        mock_session = MagicMock()
        mock_credentials = MagicMock()
        mock_session.get_credentials.return_value = mock_credentials
        
        # Mock the requests session and response
        mock_req_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": []}
        }
        
        # First call raises exception, second call succeeds
        mock_req_session.send.side_effect = [
            requests.RequestException("Network error"),
            mock_response
        ]
        
        with patch("awslabs.prometheus_mcp_server.server.boto3.Session", return_value=mock_session), \
             patch("awslabs.prometheus_mcp_server.server.requests.Session", return_value=mock_req_session), \
             patch("awslabs.prometheus_mcp_server.server.requests.Request"), \
             patch("awslabs.prometheus_mcp_server.server.SigV4Auth"), \
             patch("awslabs.prometheus_mcp_server.server.AWSRequest"), \
             patch("awslabs.prometheus_mcp_server.server.logger"), \
             patch("awslabs.prometheus_mcp_server.server.time.sleep"):  # Mock sleep to speed up test
            
            result = await PrometheusClient.make_request(
                prometheus_url="https://example.com",
                endpoint="query",
                params={"query": "up"},
                max_retries=3,
                retry_delay=1
            )
            
            assert result == {"result": []}
            assert mock_req_session.send.call_count == 2  # Called twice due to retry

    @pytest.mark.asyncio
    async def test_make_request_max_retries_exceeded(self):
        """Test that make_request raises exception when max retries are exceeded."""
        # Mock the boto3 session and credentials
        mock_session = MagicMock()
        mock_credentials = MagicMock()
        mock_session.get_credentials.return_value = mock_credentials
        
        # Mock the requests session to always raise an exception
        mock_req_session = MagicMock()
        mock_req_session.send.side_effect = requests.RequestException("Network error")
        
        with patch("awslabs.prometheus_mcp_server.server.boto3.Session", return_value=mock_session), \
             patch("awslabs.prometheus_mcp_server.server.requests.Session", return_value=mock_req_session), \
             patch("awslabs.prometheus_mcp_server.server.requests.Request"), \
             patch("awslabs.prometheus_mcp_server.server.SigV4Auth"), \
             patch("awslabs.prometheus_mcp_server.server.AWSRequest"), \
             patch("awslabs.prometheus_mcp_server.server.logger"), \
             patch("awslabs.prometheus_mcp_server.server.time.sleep"):  # Mock sleep to speed up test
            
            with pytest.raises(requests.RequestException, match="Network error"):
                await PrometheusClient.make_request(
                    prometheus_url="https://example.com",
                    endpoint="query",
                    params={"query": "up"},
                    max_retries=2,
                    retry_delay=1
                )
            
            assert mock_req_session.send.call_count == 2  # Called twice due to retry