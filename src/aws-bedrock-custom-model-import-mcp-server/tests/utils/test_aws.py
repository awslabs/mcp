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

"""Tests for the aws helper functions."""

import pytest
from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.aws import (
    get_aws_client,
    get_iam_role_arn_from_sts,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.consts import AWS_REGION
from unittest.mock import ANY, MagicMock, patch


class TestAWSClient:
    """Tests for AWS client utilities."""

    @patch('boto3.Session')
    def test_get_aws_client_with_region(self, mock_boto3_session):
        """Test getting an AWS client with region."""
        # Setup
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_boto3_session.return_value = mock_session
        mock_session.client.return_value = mock_client

        # Execute
        client = get_aws_client('bedrock', region_name='us-west-2')

        # Verify
        mock_boto3_session.assert_called_once_with(profile_name=None, region_name='us-west-2')
        mock_session.client.assert_called_once_with('bedrock', config=ANY)
        assert client == mock_client

    @patch('boto3.Session')
    def test_get_aws_client_with_default_region(self, mock_boto3_session):
        """Test getting an AWS client with default region."""
        # Setup
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_boto3_session.return_value = mock_session
        mock_session.client.return_value = mock_client

        # Execute
        client = get_aws_client('bedrock')

        # Verify
        mock_boto3_session.assert_called_once_with(profile_name=None, region_name=AWS_REGION)
        mock_session.client.assert_called_once_with('bedrock', config=ANY)
        assert client == mock_client

    @patch('boto3.Session')
    def test_get_aws_client_expired_token(self, mock_boto3_session):
        """Test error handling when credentials are expired."""
        # Setup
        mock_session = MagicMock()
        mock_boto3_session.return_value = mock_session
        mock_session.client.side_effect = Exception('ExpiredToken')

        # Execute and verify
        with pytest.raises(RuntimeError) as excinfo:
            get_aws_client('bedrock')

        # Verify the error message
        assert 'Your AWS credentials have expired' in str(excinfo.value)

    @patch('boto3.Session')
    def test_get_aws_client_no_credentials(self, mock_boto3_session):
        """Test error handling when no credentials are found."""
        # Setup
        mock_session = MagicMock()
        mock_boto3_session.return_value = mock_session
        mock_session.client.side_effect = Exception('NoCredentialProviders')

        # Execute and verify
        with pytest.raises(RuntimeError) as excinfo:
            get_aws_client('bedrock')

        # Verify the error message
        assert 'No AWS credentials found' in str(excinfo.value)

    @patch('boto3.Session')
    def test_get_aws_client_other_error(self, mock_boto3_session):
        """Test error handling for other errors."""
        # Setup
        mock_session = MagicMock()
        mock_boto3_session.return_value = mock_session
        mock_session.client.side_effect = Exception('Some other error')

        # Execute and verify
        with pytest.raises(RuntimeError) as excinfo:
            get_aws_client('bedrock')

        # Verify the error message
        assert 'Got an error when loading your client' in str(excinfo.value)

    @patch('boto3.Session')
    def test_get_iam_role_arn_from_sts_success(self, mock_boto3_session):
        """Test getting IAM role ARN from STS successfully."""
        # Setup
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_boto3_session.return_value = mock_session
        mock_session.client.return_value = mock_sts
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/test-role/session-name',
            'UserId': 'ABCD',
        }

        # Execute
        role_arn = get_iam_role_arn_from_sts()

        # Verify
        mock_session.client.assert_called_once_with('sts', config=ANY)
        mock_sts.get_caller_identity.assert_called_once()
        assert role_arn == 'arn:aws:iam::123456789012:role/test-role'

    @patch('boto3.Session')
    def test_get_iam_role_arn_from_sts_invalid_arn_format(self, mock_boto3_session):
        """Test error handling when STS ARN has invalid format."""
        # Setup
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_boto3_session.return_value = mock_session
        mock_session.client.return_value = mock_sts
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:user/test-user',  # Invalid format (not assumed-role)
            'UserId': 'ABCD',
        }

        # Execute and verify
        with pytest.raises(ValueError) as excinfo:
            get_iam_role_arn_from_sts()

        assert 'Failed to parse assumed credentials' in str(excinfo.value)

    @patch('boto3.Session')
    def test_get_iam_role_arn_from_sts_malformed_arn(self, mock_boto3_session):
        """Test error handling when STS ARN is malformed."""
        # Setup
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_boto3_session.return_value = mock_session
        mock_session.client.return_value = mock_sts
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012',  # Malformed ARN (too few parts)
            'UserId': 'ABCD',
        }

        # Execute and verify
        with pytest.raises(ValueError) as excinfo:
            get_iam_role_arn_from_sts()

        assert 'Failed to parse assumed credentials' in str(excinfo.value)

    @patch('boto3.Session')
    def test_get_iam_role_arn_from_sts_api_error(self, mock_boto3_session):
        """Test error handling when STS API call fails."""
        # Setup
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_boto3_session.return_value = mock_session
        mock_session.client.return_value = mock_sts
        mock_sts.get_caller_identity.side_effect = Exception('API Error')

        # Execute and verify
        with pytest.raises(ValueError) as excinfo:
            get_iam_role_arn_from_sts()

        assert 'Failed to parse assumed credentials' in str(excinfo.value)
        assert 'Make sure you have enough permissions' in str(excinfo.value)
