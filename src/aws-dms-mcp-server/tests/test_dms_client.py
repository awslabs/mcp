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

"""Tests for dms_client module."""

import pytest
from awslabs.aws_dms_mcp_server.config import DMSServerConfig
from awslabs.aws_dms_mcp_server.exceptions.dms_exceptions import (
    DMSAccessDeniedException,
    DMSInvalidParameterException,
    DMSMCPException,
    DMSReadOnlyModeException,
    DMSResourceNotFoundException,
)
from awslabs.aws_dms_mcp_server.utils.dms_client import DMSClient
from botocore.exceptions import ClientError
from typing import Any
from unittest.mock import MagicMock, patch


class TestDMSClientInitialization:
    """Test DMSClient initialization."""

    def test_init_with_config(self, mock_config):
        """Test client initialization with config."""
        client = DMSClient(mock_config)
        assert client.config == mock_config
        assert client._client is None

    def test_init_stores_config(self):
        """Test that config is stored properly."""
        config = DMSServerConfig(aws_region='us-west-2', read_only_mode=True)
        client = DMSClient(config)
        assert client.config.aws_region == 'us-west-2'
        assert client.config.read_only_mode is True


class TestGetClient:
    """Test get_client method."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_get_client_creates_client(self, mock_boto3, mock_config):
        """Test that get_client creates boto3 client."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        client = DMSClient(mock_config)
        result = client.get_client()

        assert result == mock_boto_client
        mock_boto3.client.assert_called_once()
        assert client._client == mock_boto_client

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_get_client_reuses_existing_client(self, mock_boto3, mock_config):
        """Test that get_client reuses existing client."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        client = DMSClient(mock_config)
        result1 = client.get_client()
        result2 = client.get_client()

        assert result1 == result2
        # Should only create client once
        assert mock_boto3.client.call_count == 1

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_get_client_with_profile(self, mock_boto3):
        """Test get_client with AWS profile."""
        config = DMSServerConfig(aws_region='us-east-1', aws_profile='test-profile')
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_boto_client = MagicMock()
        mock_session.client.return_value = mock_boto_client

        client = DMSClient(config)
        result = client.get_client()

        mock_boto3.Session.assert_called_once_with(profile_name='test-profile')
        mock_session.client.assert_called_once()
        assert result == mock_boto_client

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_get_client_without_profile(self, mock_boto3, mock_config):
        """Test get_client without AWS profile."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        client = DMSClient(mock_config)
        result = client.get_client()

        mock_boto3.client.assert_called_once()
        assert result == mock_boto_client

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_get_client_configures_retries(self, mock_boto3, mock_config):
        """Test that get_client configures retry logic."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        client = DMSClient(mock_config)
        client.get_client()

        # Verify boto3.client was called with config
        call_args = mock_boto3.client.call_args
        assert 'config' in call_args.kwargs or len(call_args.args) >= 3


class TestIsReadOnlyOperation:
    """Test is_read_only_operation method."""

    def test_read_only_operations(self, mock_config):
        """Test that read-only operations are identified correctly."""
        client = DMSClient(mock_config)

        read_only_ops = [
            'describe_replication_instances',
            'describe_endpoints',
            'describe_replication_tasks',
            'describe_table_statistics',
            'describe_connections',
            'test_connection',
        ]

        for op in read_only_ops:
            assert client.is_read_only_operation(op) is True

    def test_non_read_only_operations(self, mock_config):
        """Test that non-read-only operations are identified correctly."""
        client = DMSClient(mock_config)

        non_read_only_ops = [
            'create_replication_instance',
            'delete_endpoint',
            'start_replication_task',
            'stop_replication_task',
            'modify_replication_instance',
        ]

        for op in non_read_only_ops:
            assert client.is_read_only_operation(op) is False


class TestCallAPI:
    """Test call_api method."""

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_call_api_success(self, mock_boto3, mock_config):
        """Test successful API call."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        # Mock the describe operation
        mock_response = {'ReplicationInstances': []}
        mock_boto_client.describe_replication_instances.return_value = mock_response

        client = DMSClient(mock_config)
        result = client.call_api('describe_replication_instances')

        assert result == mock_response
        mock_boto_client.describe_replication_instances.assert_called_once()

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_call_api_with_parameters(self, mock_boto3, mock_config):
        """Test API call with parameters."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {'ReplicationInstances': []}
        mock_boto_client.describe_replication_instances.return_value = mock_response

        client = DMSClient(mock_config)
        client.call_api('describe_replication_instances', MaxRecords=100)

        mock_boto_client.describe_replication_instances.assert_called_once_with(MaxRecords=100)

    def test_call_api_read_only_mode_blocks_mutation(self):
        """Test that read-only mode blocks mutation operations."""
        config = DMSServerConfig(read_only_mode=True)
        client = DMSClient(config)

        with pytest.raises(DMSReadOnlyModeException) as exc_info:
            client.call_api('create_replication_instance', ReplicationInstanceIdentifier='test')

        assert 'create_replication_instance' in str(exc_info.value)

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_call_api_read_only_mode_allows_read(self, mock_boto3):
        """Test that read-only mode allows read operations."""
        config = DMSServerConfig(read_only_mode=True)
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        mock_response = {'ReplicationInstances': []}
        mock_boto_client.describe_replication_instances.return_value = mock_response

        client = DMSClient(config)
        result = client.call_api('describe_replication_instances')

        assert result == mock_response

    @patch('awslabs.aws_dms_mcp_server.utils.dms_client.boto3')
    def test_call_api_handles_client_error(self, mock_boto3, mock_config):
        """Test that API call handles ClientError."""
        mock_boto_client = MagicMock()
        mock_boto3.client.return_value = mock_boto_client

        # Mock ClientError
        error_response: Any = {
            'Error': {'Code': 'ResourceNotFoundFault', 'Message': 'Resource not found'},
            'ResponseMetadata': {'RequestId': '123'},
        }
        mock_boto_client.describe_replication_instances.side_effect = ClientError(
            error_response, 'describe_replication_instances'
        )

        client = DMSClient(mock_config)

        with pytest.raises(DMSResourceNotFoundException) as exc_info:
            client.call_api('describe_replication_instances')

        assert 'Resource not found' in str(exc_info.value)


class TestTranslateError:
    """Test translate_error method."""

    def test_translate_resource_not_found(self, mock_config):
        """Test translation of ResourceNotFoundFault."""
        error_response: Any = {
            'Error': {'Code': 'ResourceNotFoundFault', 'Message': 'Instance not found'},
            'ResponseMetadata': {'RequestId': 'req-123'},
        }
        client_error = ClientError(error_response, 'describe_replication_instances')

        client = DMSClient(mock_config)
        exc = client.translate_error(client_error)

        assert isinstance(exc, DMSResourceNotFoundException)
        assert 'Instance not found' in exc.message
        assert exc.details['error_code'] == 'ResourceNotFoundFault'
        assert exc.details['aws_request_id'] == 'req-123'

    def test_translate_invalid_parameter(self, mock_config):
        """Test translation of InvalidParameterValueException."""
        error_response: Any = {
            'Error': {'Code': 'InvalidParameterValueException', 'Message': 'Invalid value'},
            'ResponseMetadata': {'RequestId': 'req-456'},
        }
        client_error = ClientError(error_response, 'create_endpoint')

        client = DMSClient(mock_config)
        exc = client.translate_error(client_error)

        assert isinstance(exc, DMSInvalidParameterException)
        assert 'Invalid value' in exc.message

    def test_translate_access_denied(self, mock_config):
        """Test translation of AccessDeniedFault."""
        error_response: Any = {
            'Error': {'Code': 'AccessDeniedFault', 'Message': 'Access denied'},
            'ResponseMetadata': {'RequestId': 'req-789'},
        }
        client_error = ClientError(error_response, 'delete_endpoint')

        client = DMSClient(mock_config)
        exc = client.translate_error(client_error)

        assert isinstance(exc, DMSAccessDeniedException)
        assert 'Access denied' in exc.message

    def test_translate_unknown_error(self, mock_config):
        """Test translation of unknown error code."""
        error_response: Any = {
            'Error': {'Code': 'UnknownError', 'Message': 'Something went wrong'},
            'ResponseMetadata': {'RequestId': 'req-000'},
        }
        client_error = ClientError(error_response, 'some_operation')

        client = DMSClient(mock_config)
        exc = client.translate_error(client_error)

        assert isinstance(exc, DMSMCPException)
        assert 'Something went wrong' in exc.message
        assert exc.details['error_code'] == 'UnknownError'

    def test_translate_error_with_missing_fields(self, mock_config):
        """Test translation when error response has missing fields."""
        error_response: Any = {'Error': {}, 'ResponseMetadata': {}}
        client_error = ClientError(error_response, 'operation')

        client = DMSClient(mock_config)
        exc = client.translate_error(client_error)

        assert isinstance(exc, DMSMCPException)
        assert exc.details['error_code'] == 'Unknown'
        assert exc.details['aws_request_id'] is None


class TestReadOnlyOperationsList:
    """Test READ_ONLY_OPERATIONS class attribute."""

    def test_read_only_operations_is_set(self):
        """Test that READ_ONLY_OPERATIONS is defined."""
        assert hasattr(DMSClient, 'READ_ONLY_OPERATIONS')
        assert isinstance(DMSClient.READ_ONLY_OPERATIONS, set)

    def test_read_only_operations_contains_expected_operations(self):
        """Test that READ_ONLY_OPERATIONS contains expected operations."""
        expected_ops = {
            'describe_replication_instances',
            'describe_endpoints',
            'describe_replication_tasks',
            'describe_table_statistics',
            'describe_connections',
            'test_connection',
        }
        assert expected_ops.issubset(DMSClient.READ_ONLY_OPERATIONS)

    def test_test_connection_is_read_only(self):
        """Test that test_connection is considered read-only."""
        assert 'test_connection' in DMSClient.READ_ONLY_OPERATIONS
