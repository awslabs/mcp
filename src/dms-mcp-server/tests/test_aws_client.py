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

"""Tests for AWS client utilities."""

import pytest
from awslabs.dms_mcp_server.aws_client import (
    get_aws_region,
    get_dms_client,
    get_ec2_client,
    get_sns_client,
    handle_aws_error,
    validate_aws_credentials,
)
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from unittest.mock import ANY, Mock, patch


class TestGetAwsRegion:
    """Tests for get_aws_region function."""

    @patch.dict('os.environ', {'AWS_REGION': 'us-west-2'})
    def test_get_region_from_env_var(self):
        """Test getting region from AWS_REGION environment variable."""
        region = get_aws_region()
        assert region == 'us-west-2'

    @patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'eu-west-1'}, clear=True)
    def test_get_region_from_default_env_var(self):
        """Test getting region from AWS_DEFAULT_REGION when AWS_REGION is not set."""
        region = get_aws_region()
        assert region == 'eu-west-1'

    @patch.dict('os.environ', {}, clear=True)
    def test_get_region_default(self):
        """Test getting default region when no env vars are set."""
        region = get_aws_region()
        assert region == 'us-east-1'


class TestGetDmsClient:
    """Tests for get_dms_client function."""

    @patch('awslabs.dms_mcp_server.aws_client.boto3.client')
    def test_get_dms_client_success(self, mock_boto3_client):
        """Test successful DMS client creation."""
        mock_client = Mock()
        mock_client.describe_account_attributes.return_value = {}
        mock_boto3_client.return_value = mock_client

        client = get_dms_client()

        assert client == mock_client
        mock_boto3_client.assert_called_once_with('dms', config=ANY)
        mock_client.describe_account_attributes.assert_called_once()

    @patch('awslabs.dms_mcp_server.aws_client.boto3.client')
    def test_get_dms_client_with_region(self, mock_boto3_client):
        """Test DMS client creation with specific region."""
        mock_client = Mock()
        mock_client.describe_account_attributes.return_value = {}
        mock_boto3_client.return_value = mock_client

        client = get_dms_client(region='eu-west-1')

        assert client == mock_client
        # Verify that the config contains the correct region
        call_args = mock_boto3_client.call_args
        config = call_args[1]['config']
        assert config.region_name == 'eu-west-1'

    @patch('awslabs.dms_mcp_server.aws_client.boto3.client')
    def test_get_dms_client_credentials_error(self, mock_boto3_client):
        """Test DMS client creation with credentials error."""
        mock_boto3_client.side_effect = NoCredentialsError()

        with pytest.raises(NoCredentialsError):
            get_dms_client()


class TestGetEc2Client:
    """Tests for get_ec2_client function."""

    @patch('awslabs.dms_mcp_server.aws_client.boto3.client')
    def test_get_ec2_client_success(self, mock_boto3_client):
        """Test successful EC2 client creation."""
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        client = get_ec2_client()

        assert client == mock_client
        mock_boto3_client.assert_called_once_with('ec2', config=ANY)

    @patch('awslabs.dms_mcp_server.aws_client.boto3.client')
    def test_get_ec2_client_with_region(self, mock_boto3_client):
        """Test EC2 client creation with specific region."""
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        client = get_ec2_client(region='ap-southeast-1')

        assert client == mock_client
        call_args = mock_boto3_client.call_args
        config = call_args[1]['config']
        assert config.region_name == 'ap-southeast-1'


class TestGetSnsClient:
    """Tests for get_sns_client function."""

    @patch('awslabs.dms_mcp_server.aws_client.boto3.client')
    def test_get_sns_client_success(self, mock_boto3_client):
        """Test successful SNS client creation."""
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        client = get_sns_client()

        assert client == mock_client
        mock_boto3_client.assert_called_once_with('sns', config=ANY)


class TestHandleAwsError:
    """Tests for handle_aws_error function."""

    def test_handle_client_error_access_denied(self):
        """Test handling AccessDenied client error."""
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'AccessDenied',
                    'Message': 'User is not authorized to perform this action',
                }
            },
            operation_name='DescribeReplicationInstances',
        )

        result = handle_aws_error(error)

        assert 'AWS Error (AccessDenied)' in result
        assert 'User is not authorized to perform this action' in result

    def test_handle_client_error_resource_not_found(self):
        """Test handling ResourceNotFoundFault client error."""
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'ResourceNotFoundFault',
                    'Message': 'Replication instance not found',
                }
            },
            operation_name='DescribeReplicationInstances',
        )

        result = handle_aws_error(error)

        assert 'The requested resource was not found' in result
        assert 'Replication instance not found' in result

    def test_handle_client_error_unknown_code(self):
        """Test handling client error with unknown error code."""
        error = ClientError(
            error_response={'Error': {'Code': 'UnknownError', 'Message': 'Something went wrong'}},
            operation_name='DescribeReplicationInstances',
        )

        result = handle_aws_error(error)

        assert 'AWS Error (UnknownError)' in result
        assert 'Something went wrong' in result

    def test_handle_no_credentials_error(self):
        """Test handling NoCredentialsError."""
        error = NoCredentialsError()

        result = handle_aws_error(error)

        assert 'AWS credentials not found' in result
        assert 'configure your AWS credentials' in result

    def test_handle_partial_credentials_error(self):
        """Test handling PartialCredentialsError."""
        error = PartialCredentialsError(provider='env', cred_var='AWS_SECRET_ACCESS_KEY')

        result = handle_aws_error(error)

        assert 'Incomplete AWS credentials' in result
        assert 'ensure all required credentials are provided' in result

    def test_handle_generic_exception(self):
        """Test handling generic exception."""
        error = ValueError('Something unexpected happened')

        result = handle_aws_error(error)

        assert 'Unexpected error' in result
        assert 'Something unexpected happened' in result


class TestValidateAwsCredentials:
    """Tests for validate_aws_credentials function."""

    @patch('awslabs.dms_mcp_server.aws_client.boto3.client')
    def test_validate_credentials_success(self, mock_boto3_client):
        """Test successful credential validation."""
        mock_client = Mock()
        mock_client.get_caller_identity.return_value = {
            'UserId': 'test-user',
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:user/test-user',
        }
        mock_boto3_client.return_value = mock_client

        result = validate_aws_credentials()

        assert result is True
        mock_client.get_caller_identity.assert_called_once()

    @patch('awslabs.dms_mcp_server.aws_client.boto3.client')
    def test_validate_credentials_failure(self, mock_boto3_client):
        """Test credential validation failure."""
        mock_boto3_client.side_effect = NoCredentialsError()

        result = validate_aws_credentials()

        assert result is False

    @patch('awslabs.dms_mcp_server.aws_client.boto3.client')
    def test_get_dms_client_partial_credentials_error(self, mock_boto_client):
        """Test get_dms_client with PartialCredentialsError."""
        mock_boto_client.side_effect = PartialCredentialsError(
            provider='env', cred_var='AWS_SECRET_ACCESS_KEY'
        )

        with pytest.raises(PartialCredentialsError):
            get_dms_client()

    @patch('awslabs.dms_mcp_server.aws_client.boto3.client')
    def test_get_dms_client_client_error(self, mock_boto_client):
        """Test get_dms_client with ClientError."""
        mock_boto_client.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'CreateClient'
        )

        with pytest.raises(ClientError):
            get_dms_client()

    @patch('awslabs.dms_mcp_server.aws_client.boto3.client')
    def test_get_dms_client_generic_exception(self, mock_boto_client):
        """Test get_dms_client with generic Exception."""
        mock_boto_client.side_effect = Exception('Unexpected error')

        with pytest.raises(Exception):
            get_dms_client()
