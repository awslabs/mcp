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

"""Tests for the AWSCredentials class."""

from awslabs.prometheus_mcp_server.server import AWSCredentials
from botocore.exceptions import ClientError, NoCredentialsError
from unittest.mock import MagicMock, patch


class TestAWSCredentials:
    """Tests for the AWSCredentials class."""

    def test_validate_success_with_profile(self):
        """Test that validate returns True when credentials are valid with a profile."""
        mock_session = MagicMock()
        mock_credentials = MagicMock()
        mock_sts_client = MagicMock()

        mock_session.get_credentials.return_value = mock_credentials
        mock_session.client.return_value = mock_sts_client
        mock_sts_client.get_caller_identity.return_value = {
            'Arn': 'arn:aws:iam::123456789012:user/test-user'
        }

        with (
            patch('awslabs.prometheus_mcp_server.server.boto3.Session', return_value=mock_session),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            result = AWSCredentials.validate('us-east-1', 'test-profile')

            assert result is True
            mock_session.get_credentials.assert_called_once()
            mock_session.client.assert_called_once()
            mock_sts_client.get_caller_identity.assert_called_once()

    def test_validate_success_without_profile(self):
        """Test that validate returns True when credentials are valid without a profile."""
        mock_session = MagicMock()
        mock_credentials = MagicMock()
        mock_sts_client = MagicMock()

        mock_session.get_credentials.return_value = mock_credentials
        mock_session.client.return_value = mock_sts_client
        mock_sts_client.get_caller_identity.return_value = {
            'Arn': 'arn:aws:iam::123456789012:user/test-user'
        }

        with (
            patch('awslabs.prometheus_mcp_server.server.boto3.Session', return_value=mock_session),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            result = AWSCredentials.validate('us-east-1')

            assert result is True
            mock_session.get_credentials.assert_called_once()
            mock_session.client.assert_called_once()
            mock_sts_client.get_caller_identity.assert_called_once()

    def test_validate_no_credentials(self):
        """Test that validate returns False when no credentials are found."""
        mock_session = MagicMock()
        mock_session.get_credentials.return_value = None

        with (
            patch('awslabs.prometheus_mcp_server.server.boto3.Session', return_value=mock_session),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            result = AWSCredentials.validate('us-east-1')

            assert result is False
            mock_session.get_credentials.assert_called_once()

    def test_validate_no_credentials_error(self):
        """Test that validate returns False when NoCredentialsError is raised."""
        mock_session = MagicMock()
        mock_session.get_credentials.side_effect = NoCredentialsError()

        with (
            patch('awslabs.prometheus_mcp_server.server.boto3.Session', return_value=mock_session),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            result = AWSCredentials.validate('us-east-1')

            assert result is False
            mock_session.get_credentials.assert_called_once()

    def test_validate_client_error(self):
        """Test that validate returns False when ClientError is raised."""
        mock_session = MagicMock()
        mock_credentials = MagicMock()
        mock_session.get_credentials.return_value = mock_credentials
        mock_session.client.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}}, 'GetCallerIdentity'
        )

        with (
            patch('awslabs.prometheus_mcp_server.server.boto3.Session', return_value=mock_session),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            result = AWSCredentials.validate('us-east-1')

            assert result is False
            mock_session.get_credentials.assert_called_once()
            mock_session.client.assert_called_once()
