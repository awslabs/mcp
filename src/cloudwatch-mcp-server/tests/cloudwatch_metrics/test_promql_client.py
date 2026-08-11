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
"""Tests for the PromQL client."""

import pytest
import requests
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client import PromQLClient
from unittest.mock import MagicMock, patch


class TestPromQLClient:
    """Tests for PromQLClient."""

    def test_get_base_url(self):
        """Test base URL construction."""
        assert (
            PromQLClient._get_base_url('us-east-1')
            == 'https://monitoring.us-east-1.amazonaws.com/api/v1'
        )
        assert (
            PromQLClient._get_base_url('eu-west-1')
            == 'https://monitoring.eu-west-1.amazonaws.com/api/v1'
        )

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.SigV4Auth')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.requests.Session')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.Session')
    def test_make_request_success(self, mock_boto_session, mock_req_session, mock_sigv4):
        """Test successful request."""
        # Setup boto3 session mock
        mock_creds = MagicMock()
        mock_boto_session.return_value.get_credentials.return_value = mock_creds

        # Setup requests mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'success',
            'data': {'resultType': 'vector', 'result': []},
        }
        mock_response.raise_for_status = MagicMock()
        mock_req_session.return_value.__enter__.return_value.send.return_value = mock_response

        result = PromQLClient.make_request(
            endpoint='query',
            params={'query': 'up'},
            region='us-east-1',
        )

        assert result == {'resultType': 'vector', 'result': []}

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.SigV4Auth')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.requests.Session')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.Session')
    def test_make_request_api_error(self, mock_boto_session, mock_req_session, mock_sigv4):
        """Test API error response raises RuntimeError."""
        mock_creds = MagicMock()
        mock_boto_session.return_value.get_credentials.return_value = mock_creds

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'error',
            'error': 'bad query syntax',
        }
        mock_response.raise_for_status = MagicMock()
        mock_req_session.return_value.__enter__.return_value.send.return_value = mock_response

        with pytest.raises(RuntimeError, match='PromQL API error: bad query syntax'):
            PromQLClient.make_request(
                endpoint='query',
                params={'query': 'invalid{'},
                region='us-east-1',
            )

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.Session')
    def test_make_request_no_credentials(self, mock_boto_session):
        """Test missing credentials raises ValueError."""
        mock_boto_session.return_value.get_credentials.return_value = None

        with pytest.raises(ValueError, match='AWS credentials not found'):
            PromQLClient.make_request(
                endpoint='query',
                params={'query': 'up'},
                region='us-east-1',
            )

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.SigV4Auth')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.time_module.sleep')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.requests.Session')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.Session')
    def test_make_request_retry_on_network_error(
        self, mock_boto_session, mock_req_session, mock_sleep, mock_sigv4
    ):
        """Test retry logic on network errors."""
        mock_creds = MagicMock()
        mock_boto_session.return_value.get_credentials.return_value = mock_creds

        mock_req_session.return_value.__enter__.return_value.send.side_effect = (
            requests.ConnectionError('Connection refused')
        )

        with pytest.raises(requests.ConnectionError):
            PromQLClient.make_request(
                endpoint='query',
                params={'query': 'up'},
                region='us-east-1',
            )

        # Should have retried (sleep called MAX_RETRIES - 1 times)
        assert mock_sleep.call_count == 2

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.SigV4Auth')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.requests.Session')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.Session')
    def test_make_request_uses_profile(self, mock_boto_session, mock_req_session, mock_sigv4):
        """Test that profile_name is passed to boto3 Session."""
        mock_creds = MagicMock()
        mock_boto_session.return_value.get_credentials.return_value = mock_creds

        mock_response = MagicMock()
        mock_response.json.return_value = {'status': 'success', 'data': []}
        mock_response.raise_for_status = MagicMock()
        mock_req_session.return_value.__enter__.return_value.send.return_value = mock_response

        PromQLClient.make_request(
            endpoint='labels',
            params={},
            region='us-west-2',
            profile_name='my-profile',
        )

        mock_boto_session.assert_called_with(profile_name='my-profile', region_name='us-west-2')

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.SigV4Auth')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.time_module.sleep')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.requests.Session')
    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_client.Session')
    def test_make_request_retry_then_success(
        self, mock_boto_session, mock_req_session, mock_sleep, mock_sigv4
    ):
        """Test retry succeeds on second attempt."""
        mock_creds = MagicMock()
        mock_boto_session.return_value.get_credentials.return_value = mock_creds

        mock_response_ok = MagicMock()
        mock_response_ok.json.return_value = {'status': 'success', 'data': ['metric1']}
        mock_response_ok.raise_for_status = MagicMock()

        mock_req_session.return_value.__enter__.return_value.send.side_effect = [
            requests.ConnectionError('timeout'),
            mock_response_ok,
        ]

        result = PromQLClient.make_request(
            endpoint='labels',
            params={},
            region='us-east-1',
        )

        assert result == ['metric1']
        assert mock_sleep.call_count == 1
