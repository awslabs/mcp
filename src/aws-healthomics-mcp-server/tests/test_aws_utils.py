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

"""Unit tests for AWS utility functions."""

import base64
import io
import os
import pytest
import zipfile
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    create_aws_client,
    create_zip_file,
    decode_from_base64,
    encode_to_base64,
    get_aws_session,
    get_logs_client,
    get_omics_client,
    get_ssm_client,
)
from unittest.mock import MagicMock, patch


class TestGetAwsSession:
    """Test cases for get_aws_session function."""

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.boto3.Session')
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.botocore.session.Session')
    def test_get_aws_session_with_region(self, mock_botocore_session, mock_boto3_session):
        """Test get_aws_session with explicit region."""
        mock_botocore_instance = MagicMock()
        mock_botocore_session.return_value = mock_botocore_instance
        mock_boto3_instance = MagicMock()
        mock_boto3_session.return_value = mock_boto3_instance

        result = get_aws_session('us-west-2')

        mock_botocore_session.assert_called_once()
        mock_boto3_session.assert_called_once_with(
            region_name='us-west-2', botocore_session=mock_botocore_instance
        )
        assert result == mock_boto3_instance
        assert 'awslabs/mcp/aws-healthomics-mcp-server/' in mock_botocore_instance.user_agent_extra

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.boto3.Session')
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.botocore.session.Session')
    @patch.dict(os.environ, {'AWS_REGION': 'eu-west-1'})
    def test_get_aws_session_with_env_region(self, mock_botocore_session, mock_boto3_session):
        """Test get_aws_session with region from environment."""
        mock_botocore_instance = MagicMock()
        mock_botocore_session.return_value = mock_botocore_instance
        mock_boto3_instance = MagicMock()
        mock_boto3_session.return_value = mock_boto3_instance

        result = get_aws_session()

        mock_boto3_session.assert_called_once_with(
            region_name='eu-west-1', botocore_session=mock_botocore_instance
        )
        assert result == mock_boto3_instance

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.boto3.Session')
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.botocore.session.Session')
    @patch.dict(os.environ, {}, clear=True)
    def test_get_aws_session_default_region(self, mock_botocore_session, mock_boto3_session):
        """Test get_aws_session with default region."""
        mock_botocore_instance = MagicMock()
        mock_botocore_session.return_value = mock_botocore_instance
        mock_boto3_instance = MagicMock()
        mock_boto3_session.return_value = mock_boto3_instance

        result = get_aws_session()

        mock_boto3_session.assert_called_once_with(
            region_name='us-east-1', botocore_session=mock_botocore_instance
        )
        assert result == mock_boto3_instance


class TestCreateAwsClient:
    """Test cases for create_aws_client function."""

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_create_aws_client_success(self, mock_get_session):
        """Test successful client creation."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = create_aws_client('s3', 'us-west-2')

        mock_get_session.assert_called_once_with('us-west-2')
        mock_session.client.assert_called_once_with('s3')
        assert result == mock_client

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    @patch.dict(os.environ, {'AWS_REGION': 'ap-southeast-1'})
    def test_create_aws_client_with_env_region(self, mock_get_session):
        """Test client creation with region from environment."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = create_aws_client('dynamodb')

        mock_get_session.assert_called_once_with('ap-southeast-1')
        mock_session.client.assert_called_once_with('dynamodb')
        assert result == mock_client

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_create_aws_client_failure(self, mock_get_session):
        """Test client creation failure."""
        mock_session = MagicMock()
        mock_session.client.side_effect = Exception('Client creation failed')
        mock_get_session.return_value = mock_session

        with pytest.raises(Exception, match='Client creation failed'):
            create_aws_client('invalid-service')


class TestGetOmicsClient:
    """Test cases for get_omics_client function."""

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_get_omics_client_success(self, mock_get_session):
        """Test successful HealthOmics client creation."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = get_omics_client('us-east-1')

        mock_get_session.assert_called_once_with('us-east-1')
        mock_session.client.assert_called_once_with('omics')
        assert result == mock_client

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    @patch.dict(os.environ, {'AWS_REGION': 'eu-central-1'})
    def test_get_omics_client_with_env_region(self, mock_get_session):
        """Test HealthOmics client creation with region from environment."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = get_omics_client()

        mock_get_session.assert_called_once_with('eu-central-1')
        mock_session.client.assert_called_once_with('omics')
        assert result == mock_client

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_get_omics_client_failure(self, mock_get_session):
        """Test HealthOmics client creation failure."""
        mock_session = MagicMock()
        mock_session.client.side_effect = Exception('HealthOmics not available')
        mock_get_session.return_value = mock_session

        with pytest.raises(Exception, match='HealthOmics not available'):
            get_omics_client()


class TestGetLogsClient:
    """Test cases for get_logs_client function."""

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_get_logs_client_success(self, mock_get_session):
        """Test successful CloudWatch Logs client creation."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = get_logs_client('us-west-1')

        mock_get_session.assert_called_once_with('us-west-1')
        mock_session.client.assert_called_once_with('logs')
        assert result == mock_client

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    @patch.dict(os.environ, {}, clear=True)
    def test_get_logs_client_default_region(self, mock_get_session):
        """Test CloudWatch Logs client creation with default region."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = get_logs_client()

        mock_get_session.assert_called_once_with('us-east-1')
        mock_session.client.assert_called_once_with('logs')
        assert result == mock_client

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_get_logs_client_failure(self, mock_get_session):
        """Test CloudWatch Logs client creation failure."""
        mock_session = MagicMock()
        mock_session.client.side_effect = Exception('Logs service unavailable')
        mock_get_session.return_value = mock_session

        with pytest.raises(Exception, match='Logs service unavailable'):
            get_logs_client()


class TestGetSsmClient:
    """Test cases for get_ssm_client function."""

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_get_ssm_client_success(self, mock_get_session):
        """Test successful SSM client creation."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = get_ssm_client('ap-northeast-1')

        mock_get_session.assert_called_once_with('ap-northeast-1')
        mock_session.client.assert_called_once_with('ssm')
        assert result == mock_client

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    @patch.dict(os.environ, {'AWS_REGION': 'ca-central-1'})
    def test_get_ssm_client_with_env_region(self, mock_get_session):
        """Test SSM client creation with region from environment."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = get_ssm_client()

        mock_get_session.assert_called_once_with('ca-central-1')
        mock_session.client.assert_called_once_with('ssm')
        assert result == mock_client

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_get_ssm_client_failure(self, mock_get_session):
        """Test SSM client creation failure."""
        mock_session = MagicMock()
        mock_session.client.side_effect = Exception('SSM access denied')
        mock_get_session.return_value = mock_session

        with pytest.raises(Exception, match='SSM access denied'):
            get_ssm_client()


class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_create_zip_file_single_file(self):
        """Test creating a ZIP file with a single file."""
        files = {'test.txt': 'Hello, World!'}
        zip_data = create_zip_file(files)

        # Verify it's valid ZIP data
        assert isinstance(zip_data, bytes)
        assert len(zip_data) > 0

        # Verify ZIP contents
        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_file:
            assert zip_file.namelist() == ['test.txt']
            assert zip_file.read('test.txt').decode('utf-8') == 'Hello, World!'

    def test_create_zip_file_multiple_files(self):
        """Test creating a ZIP file with multiple files."""
        files = {
            'file1.txt': 'Content 1',
            'file2.txt': 'Content 2',
            'subdir/file3.txt': 'Content 3',
        }
        zip_data = create_zip_file(files)

        # Verify ZIP contents
        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_file:
            names = sorted(zip_file.namelist())
            assert names == ['file1.txt', 'file2.txt', 'subdir/file3.txt']
            assert zip_file.read('file1.txt').decode('utf-8') == 'Content 1'
            assert zip_file.read('file2.txt').decode('utf-8') == 'Content 2'
            assert zip_file.read('subdir/file3.txt').decode('utf-8') == 'Content 3'

    def test_create_zip_file_empty_dict(self):
        """Test creating a ZIP file with empty dictionary."""
        files = {}
        zip_data = create_zip_file(files)

        # Verify it's valid ZIP data
        assert isinstance(zip_data, bytes)
        assert len(zip_data) > 0

        # Verify ZIP is empty
        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_file:
            assert zip_file.namelist() == []

    def test_encode_to_base64(self):
        """Test base64 encoding."""
        data = b'Hello, World!'
        result = encode_to_base64(data)
        expected = base64.b64encode(data).decode('utf-8')
        assert result == expected
        assert isinstance(result, str)

    def test_encode_to_base64_empty(self):
        """Test base64 encoding of empty bytes."""
        data = b''
        result = encode_to_base64(data)
        assert result == ''

    def test_decode_from_base64(self):
        """Test base64 decoding."""
        original_data = b'Hello, World!'
        encoded = base64.b64encode(original_data).decode('utf-8')
        result = decode_from_base64(encoded)
        assert result == original_data
        assert isinstance(result, bytes)

    def test_decode_from_base64_empty(self):
        """Test base64 decoding of empty string."""
        result = decode_from_base64('')
        assert result == b''

    def test_base64_round_trip(self):
        """Test encoding and decoding round trip."""
        original_data = b'This is a test message with special chars: !@#$%^&*()'
        encoded = encode_to_base64(original_data)
        decoded = decode_from_base64(encoded)
        assert decoded == original_data


class TestRegionResolution:
    """Test cases for region resolution across client functions."""

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    @patch.dict(os.environ, {}, clear=True)
    def test_all_clients_use_default_region(self, mock_get_session):
        """Test that all client functions use default region when none specified."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        # Test each client function
        get_omics_client()
        get_logs_client()
        get_ssm_client()
        create_aws_client('s3')

        # Verify all calls used default region
        expected_calls = [
            ('us-east-1',),  # get_omics_client
            ('us-east-1',),  # get_logs_client
            ('us-east-1',),  # get_ssm_client
            ('us-east-1',),  # create_aws_client
        ]
        actual_calls = [call.args for call in mock_get_session.call_args_list]
        assert actual_calls == expected_calls

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    @patch.dict(os.environ, {'AWS_REGION': 'eu-west-2'})
    def test_all_clients_use_env_region(self, mock_get_session):
        """Test that all client functions use environment region when available."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        # Test each client function
        get_omics_client()
        get_logs_client()
        get_ssm_client()
        create_aws_client('dynamodb')

        # Verify all calls used environment region
        expected_calls = [
            ('eu-west-2',),  # get_omics_client
            ('eu-west-2',),  # get_logs_client
            ('eu-west-2',),  # get_ssm_client
            ('eu-west-2',),  # create_aws_client
        ]
        actual_calls = [call.args for call in mock_get_session.call_args_list]
        assert actual_calls == expected_calls

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_explicit_region_overrides_env(self, mock_get_session):
        """Test that explicit region parameter overrides environment."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        # Test each client function with explicit region
        get_omics_client('us-west-1')
        get_logs_client('us-west-1')
        get_ssm_client('us-west-1')
        create_aws_client('ec2', 'us-west-1')

        # Verify all calls used explicit region
        expected_calls = [
            ('us-west-1',),  # get_omics_client
            ('us-west-1',),  # get_logs_client
            ('us-west-1',),  # get_ssm_client
            ('us-west-1',),  # create_aws_client
        ]
        actual_calls = [call.args for call in mock_get_session.call_args_list]
        assert actual_calls == expected_calls
