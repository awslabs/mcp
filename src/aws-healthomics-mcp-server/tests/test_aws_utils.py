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
    get_omics_endpoint_url,
    get_omics_service_name,
    get_region,
    get_ssm_client,
)
from unittest.mock import MagicMock, patch


class TestGetRegion:
    """Test cases for get_region function."""

    @patch.dict(os.environ, {'AWS_REGION': 'ap-southeast-2'})
    def test_get_region_from_environment(self):
        """Test get_region returns region from environment variable."""
        result = get_region()
        assert result == 'ap-southeast-2'

    @patch.dict(os.environ, {}, clear=True)
    def test_get_region_default(self):
        """Test get_region returns default region when no environment variable."""
        result = get_region()
        assert result == 'us-east-1'

    @patch.dict(os.environ, {'AWS_REGION': ''})
    def test_get_region_empty_env_var(self):
        """Test get_region returns empty string when environment variable is set to empty."""
        result = get_region()
        assert result == ''


class TestGetOmicsServiceName:
    """Test cases for get_omics_service_name function."""

    @patch.dict(os.environ, {'HEALTHOMICS_SERVICE_NAME': 'custom-omics'})
    def test_get_omics_service_name_from_environment(self):
        """Test get_omics_service_name returns service name from environment variable."""
        result = get_omics_service_name()
        assert result == 'custom-omics'

    @patch.dict(os.environ, {}, clear=True)
    def test_get_omics_service_name_default(self):
        """Test get_omics_service_name returns default service name when no environment variable."""
        result = get_omics_service_name()
        assert result == 'omics'

    @patch.dict(os.environ, {'HEALTHOMICS_SERVICE_NAME': ''})
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.logger')
    def test_get_omics_service_name_empty_env_var(self, mock_logger):
        """Test get_omics_service_name returns default and logs warning when environment variable is empty."""
        result = get_omics_service_name()
        assert result == 'omics'
        mock_logger.warning.assert_called_once_with(
            'HEALTHOMICS_SERVICE_NAME environment variable is empty or contains only whitespace. '
            'Using default service name: omics'
        )

    @patch.dict(os.environ, {'HEALTHOMICS_SERVICE_NAME': '   '})
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.logger')
    def test_get_omics_service_name_whitespace_env_var(self, mock_logger):
        """Test get_omics_service_name returns default and logs warning when environment variable is only whitespace."""
        result = get_omics_service_name()
        assert result == 'omics'
        mock_logger.warning.assert_called_once_with(
            'HEALTHOMICS_SERVICE_NAME environment variable is empty or contains only whitespace. '
            'Using default service name: omics'
        )

    @patch.dict(os.environ, {'HEALTHOMICS_SERVICE_NAME': '\t\n  \r'})
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.logger')
    def test_get_omics_service_name_mixed_whitespace_env_var(self, mock_logger):
        """Test get_omics_service_name returns default and logs warning when environment variable contains mixed whitespace."""
        result = get_omics_service_name()
        assert result == 'omics'
        mock_logger.warning.assert_called_once_with(
            'HEALTHOMICS_SERVICE_NAME environment variable is empty or contains only whitespace. '
            'Using default service name: omics'
        )

    @patch.dict(os.environ, {'HEALTHOMICS_SERVICE_NAME': 'omics-dev'})
    def test_get_omics_service_name_custom_value(self):
        """Test get_omics_service_name with custom service name."""
        result = get_omics_service_name()
        assert result == 'omics-dev'

    @patch.dict(os.environ, {'HEALTHOMICS_SERVICE_NAME': '  omics-staging  '})
    def test_get_omics_service_name_with_surrounding_whitespace(self):
        """Test get_omics_service_name strips surrounding whitespace from valid service name."""
        result = get_omics_service_name()
        assert result == 'omics-staging'

    @patch.dict(os.environ, {'HEALTHOMICS_SERVICE_NAME': 'omics-prod'})
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.logger')
    def test_get_omics_service_name_valid_no_warning(self, mock_logger):
        """Test get_omics_service_name does not log warning for valid service name."""
        result = get_omics_service_name()
        assert result == 'omics-prod'
        mock_logger.warning.assert_not_called()


class TestGetOmicsEndpointUrl:
    """Test cases for get_omics_endpoint_url function."""

    @patch.dict(os.environ, {}, clear=True)
    def test_get_omics_endpoint_url_not_set(self):
        """Test get_omics_endpoint_url returns None when environment variable is not set."""
        result = get_omics_endpoint_url()
        assert result is None

    @patch.dict(os.environ, {'HEALTHOMICS_ENDPOINT_URL': 'https://omics.us-west-2.amazonaws.com'})
    def test_get_omics_endpoint_url_valid_https(self):
        """Test get_omics_endpoint_url returns valid HTTPS URL."""
        result = get_omics_endpoint_url()
        assert result == 'https://omics.us-west-2.amazonaws.com'

    @patch.dict(os.environ, {'HEALTHOMICS_ENDPOINT_URL': 'http://localhost:8080'})
    def test_get_omics_endpoint_url_valid_http(self):
        """Test get_omics_endpoint_url returns valid HTTP URL."""
        result = get_omics_endpoint_url()
        assert result == 'http://localhost:8080'

    @patch.dict(os.environ, {'HEALTHOMICS_ENDPOINT_URL': ''})
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.logger')
    def test_get_omics_endpoint_url_empty_string(self, mock_logger):
        """Test get_omics_endpoint_url returns None and logs warning for empty string."""
        result = get_omics_endpoint_url()
        assert result is None
        mock_logger.warning.assert_called_once_with(
            'HEALTHOMICS_ENDPOINT_URL environment variable is empty or contains only whitespace. '
            'Using default endpoint.'
        )

    @patch.dict(os.environ, {'HEALTHOMICS_ENDPOINT_URL': '   '})
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.logger')
    def test_get_omics_endpoint_url_whitespace_only(self, mock_logger):
        """Test get_omics_endpoint_url returns None and logs warning for whitespace-only string."""
        result = get_omics_endpoint_url()
        assert result is None
        mock_logger.warning.assert_called_once_with(
            'HEALTHOMICS_ENDPOINT_URL environment variable is empty or contains only whitespace. '
            'Using default endpoint.'
        )

    @patch.dict(os.environ, {'HEALTHOMICS_ENDPOINT_URL': 'invalid-url'})
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.logger')
    def test_get_omics_endpoint_url_invalid_protocol(self, mock_logger):
        """Test get_omics_endpoint_url returns None and logs warning for invalid protocol."""
        result = get_omics_endpoint_url()
        assert result is None
        mock_logger.warning.assert_called_once_with(
            'HEALTHOMICS_ENDPOINT_URL environment variable "invalid-url" must begin with '
            'http:// or https://. Using default endpoint.'
        )

    @patch.dict(os.environ, {'HEALTHOMICS_ENDPOINT_URL': 'ftp://example.com'})
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.logger')
    def test_get_omics_endpoint_url_wrong_protocol(self, mock_logger):
        """Test get_omics_endpoint_url returns None and logs warning for wrong protocol."""
        result = get_omics_endpoint_url()
        assert result is None
        mock_logger.warning.assert_called_once_with(
            'HEALTHOMICS_ENDPOINT_URL environment variable "ftp://example.com" must begin with '
            'http:// or https://. Using default endpoint.'
        )

    @patch.dict(os.environ, {'HEALTHOMICS_ENDPOINT_URL': '  https://example.com  '})
    def test_get_omics_endpoint_url_with_surrounding_whitespace(self):
        """Test get_omics_endpoint_url strips surrounding whitespace from valid URL."""
        result = get_omics_endpoint_url()
        assert result == 'https://example.com'

    @patch.dict(
        os.environ, {'HEALTHOMICS_ENDPOINT_URL': 'https://omics-dev.example.com:8443/path'}
    )
    def test_get_omics_endpoint_url_complex_url(self):
        """Test get_omics_endpoint_url handles complex URLs with port and path."""
        result = get_omics_endpoint_url()
        assert result == 'https://omics-dev.example.com:8443/path'

    @patch.dict(os.environ, {'HEALTHOMICS_ENDPOINT_URL': 'https://valid.com'})
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.logger')
    def test_get_omics_endpoint_url_valid_no_warning(self, mock_logger):
        """Test get_omics_endpoint_url does not log warning for valid URL."""
        result = get_omics_endpoint_url()
        assert result == 'https://valid.com'
        mock_logger.warning.assert_not_called()


class TestGetAwsSession:
    """Test cases for get_aws_session function."""

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
        assert 'awslabs/mcp/aws-healthomics-mcp-server/' in mock_botocore_instance.user_agent_extra

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

        result = create_aws_client('s3')

        mock_get_session.assert_called_once_with()
        mock_session.client.assert_called_once_with('s3')
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
    @patch.dict(os.environ, {}, clear=True)
    def test_get_omics_client_success_default_service_no_endpoint(self, mock_get_session):
        """Test successful HealthOmics client creation with default service name and no endpoint URL."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = get_omics_client()

        mock_session.client.assert_called_once_with('omics')
        assert result == mock_client

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    @patch.dict(os.environ, {'HEALTHOMICS_SERVICE_NAME': 'custom-omics'})
    def test_get_omics_client_success_custom_service_no_endpoint(self, mock_get_session):
        """Test successful HealthOmics client creation with custom service name and no endpoint URL."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = get_omics_client()

        mock_session.client.assert_called_once_with('custom-omics')
        assert result == mock_client

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    @patch.dict(os.environ, {'HEALTHOMICS_ENDPOINT_URL': 'https://omics.us-west-2.amazonaws.com'})
    def test_get_omics_client_success_with_endpoint_url(self, mock_get_session):
        """Test successful HealthOmics client creation with custom endpoint URL."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = get_omics_client()

        mock_session.client.assert_called_once_with(
            'omics', endpoint_url='https://omics.us-west-2.amazonaws.com'
        )
        assert result == mock_client

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    @patch.dict(
        os.environ,
        {
            'HEALTHOMICS_SERVICE_NAME': 'omics-dev',
            'HEALTHOMICS_ENDPOINT_URL': 'http://localhost:8080',
        },
    )
    def test_get_omics_client_success_custom_service_and_endpoint(self, mock_get_session):
        """Test successful HealthOmics client creation with custom service name and endpoint URL."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = get_omics_client()

        mock_session.client.assert_called_once_with(
            'omics-dev', endpoint_url='http://localhost:8080'
        )
        assert result == mock_client

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    @patch.dict(os.environ, {'HEALTHOMICS_ENDPOINT_URL': 'invalid-url'})
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.logger')
    def test_get_omics_client_success_invalid_endpoint_url(self, mock_logger, mock_get_session):
        """Test HealthOmics client creation with invalid endpoint URL falls back to default."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = get_omics_client()

        # Should call without endpoint_url since invalid URL is ignored
        mock_session.client.assert_called_once_with('omics')
        mock_logger.warning.assert_called_once()
        assert result == mock_client

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    @patch.dict(os.environ, {}, clear=True)
    def test_get_omics_client_failure(self, mock_get_session):
        """Test HealthOmics client creation failure."""
        mock_session = MagicMock()
        mock_session.client.side_effect = Exception('HealthOmics not available')
        mock_get_session.return_value = mock_session

        with pytest.raises(Exception, match='HealthOmics not available'):
            get_omics_client()

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    @patch.dict(os.environ, {'HEALTHOMICS_ENDPOINT_URL': 'https://invalid.endpoint.com'})
    def test_get_omics_client_failure_with_endpoint(self, mock_get_session):
        """Test HealthOmics client creation failure with custom endpoint URL."""
        mock_session = MagicMock()
        mock_session.client.side_effect = Exception('Endpoint not reachable')
        mock_get_session.return_value = mock_session

        with pytest.raises(Exception, match='Endpoint not reachable'):
            get_omics_client()


class TestGetLogsClient:
    """Test cases for get_logs_client function."""

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.create_aws_client')
    def test_get_logs_client_success(self, mock_create_client):
        """Test successful CloudWatch Logs client creation."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        result = get_logs_client()

        mock_create_client.assert_called_once_with('logs')
        assert result == mock_client

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.create_aws_client')
    def test_get_logs_client_failure(self, mock_create_client):
        """Test CloudWatch Logs client creation failure."""
        mock_create_client.side_effect = Exception('Logs service unavailable')

        with pytest.raises(Exception, match='Logs service unavailable'):
            get_logs_client()


class TestGetSsmClient:
    """Test cases for get_ssm_client function."""

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.create_aws_client')
    def test_get_ssm_client_success(self, mock_create_client):
        """Test successful SSM client creation."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        result = get_ssm_client()

        mock_create_client.assert_called_once_with('ssm')
        assert result == mock_client

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.create_aws_client')
    def test_get_ssm_client_failure(self, mock_create_client):
        """Test SSM client creation failure."""
        mock_create_client.side_effect = Exception('SSM access denied')

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

        # Verify all calls used no region parameter (centralized)
        expected_calls = [(), (), (), ()]  # All calls should have no arguments
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

        # Verify all calls used no region parameter (centralized)
        expected_calls = [(), (), (), ()]  # All calls should have no arguments
        actual_calls = [call.args for call in mock_get_session.call_args_list]
        assert actual_calls == expected_calls


class TestServiceNameAndEndpointConfiguration:
    """Test cases for service name and endpoint URL configuration integration."""

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_omics_service_name')
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_omics_endpoint_url')
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_get_omics_client_uses_configuration_functions(
        self, mock_get_session, mock_get_endpoint, mock_get_service_name
    ):
        """Test that get_omics_client uses both configuration functions."""
        mock_get_service_name.return_value = 'test-service'
        mock_get_endpoint.return_value = 'https://test.endpoint.com'
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = get_omics_client()

        mock_get_service_name.assert_called_once_with()
        mock_get_endpoint.assert_called_once_with()
        mock_session.client.assert_called_once_with(
            'test-service', endpoint_url='https://test.endpoint.com'
        )
        assert result == mock_client

    @patch.dict(os.environ, {'HEALTHOMICS_SERVICE_NAME': 'omics-staging'})
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_end_to_end_service_name_configuration(self, mock_get_session):
        """Test end-to-end service name configuration from environment to client creation."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = get_omics_client()

        mock_session.client.assert_called_once_with('omics-staging')
        assert result == mock_client

    @patch.dict(os.environ, {'HEALTHOMICS_ENDPOINT_URL': 'https://omics.example.com'})
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_end_to_end_endpoint_url_configuration(self, mock_get_session):
        """Test end-to-end endpoint URL configuration from environment to client creation."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = get_omics_client()

        mock_session.client.assert_called_once_with(
            'omics', endpoint_url='https://omics.example.com'
        )
        assert result == mock_client

    @patch.dict(
        os.environ,
        {
            'HEALTHOMICS_SERVICE_NAME': 'omics-dev',
            'HEALTHOMICS_ENDPOINT_URL': 'http://localhost:9000',
        },
    )
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    def test_end_to_end_both_configurations(self, mock_get_session):
        """Test end-to-end configuration of both service name and endpoint URL."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = get_omics_client()

        mock_session.client.assert_called_once_with(
            'omics-dev', endpoint_url='http://localhost:9000'
        )
        assert result == mock_client

    @patch.dict(os.environ, {'HEALTHOMICS_SERVICE_NAME': '   '})
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.logger')
    def test_end_to_end_whitespace_service_name_fallback(self, mock_logger, mock_get_session):
        """Test end-to-end fallback to default when service name is whitespace."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = get_omics_client()

        mock_session.client.assert_called_once_with('omics')
        mock_logger.warning.assert_called_once()
        assert result == mock_client

    @patch.dict(os.environ, {'HEALTHOMICS_ENDPOINT_URL': 'invalid-url'})
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_aws_session')
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.logger')
    def test_end_to_end_invalid_endpoint_url_fallback(self, mock_logger, mock_get_session):
        """Test end-to-end fallback to default endpoint when URL is invalid."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_get_session.return_value = mock_session

        result = get_omics_client()

        mock_session.client.assert_called_once_with('omics')
        mock_logger.warning.assert_called_once()
        assert result == mock_client
