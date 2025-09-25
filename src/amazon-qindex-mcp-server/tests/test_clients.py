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

"""Tests for the sub clients file on amazon-qindex MCP Server."""

import pytest
from awslabs.amazon_qindex_mcp_server.clients import QBusinessClient, QBusinessClientError
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Any, cast
from unittest.mock import Mock, patch


class TestQBusinessClient:
    """Test cases for the QBusinessClient class."""

    @pytest.fixture
    def client(self):
        """Return a QBusinessClient instance for testing."""
        return QBusinessClient(
            region_name='us-east-1',
            aws_access_key_id='test-key',
            aws_secret_access_key='test-secret',  # pragma: allowlist secret
            aws_session_token='test-token',
        )

    @pytest.fixture
    def mock_boto3_session(self):
        """Create a mock boto3 session with proper parameter validation bypass."""
        with patch('boto3.Session') as mock_session:
            mock_client = Mock()
            # Prevent parameter validation from boto3
            mock_client.meta.events.register.return_value = None

            # Mock the client creation with config parameter
            def client_creator(*args, **kwargs):
                # Verify config is properly passed
                assert 'config' in kwargs
                assert isinstance(kwargs['config'], Config)
                return mock_client

            mock_session.return_value.client = client_creator
            yield mock_session, mock_client

    def test_init_with_credentials(self, mock_boto3_session):
        """Test client initialization with credentials."""
        mock_session, _ = mock_boto3_session
        client = QBusinessClient(
            region_name='us-east-1',
            aws_access_key_id='test-key',
            aws_secret_access_key='test-secret',  # pragma: allowlist secret
            aws_session_token='test-token',
        )
        assert isinstance(client, QBusinessClient)
        mock_session.assert_called_once_with(
            aws_access_key_id='test-key',
            aws_secret_access_key='test-secret',  # pragma: allowlist secret
            aws_session_token='test-token',
            region_name='us-east-1',
        )

    def test_init_without_credentials(self, mock_boto3_session):
        """Test client initialization without credentials."""
        mock_session, _ = mock_boto3_session
        client = QBusinessClient(region_name='us-east-1')
        assert isinstance(client, QBusinessClient)
        mock_session.assert_called_once_with(
            aws_access_key_id=None,
            aws_secret_access_key=None,  # pragma: allowlist secret
            aws_session_token=None,
            region_name='us-east-1',
        )

    def test_validate_attribute_filter_invalid_types(self, client):
        """Test attribute filter validation with invalid types."""
        # Test non-dictionary input
        with pytest.raises(ValueError, match='attribute_filter must be a dictionary'):
            client._validate_attribute_filter([])

        # Test invalid attributeValue type
        with pytest.raises(ValueError, match='attributeValue must be a dictionary'):
            client._validate_attribute_filter(
                {'attributeName': 'test', 'attributeValue': 'not_a_dict'}
            )

        # Test missing valid value type
        with pytest.raises(ValueError, match='attributeValue must contain one of:'):
            client._validate_attribute_filter(
                {'attributeName': 'test', 'attributeValue': {'InvalidType': 'value'}}
            )

    def test_validate_content_source_invalid_types(self, client):
        """Test content source validation with invalid types."""
        # Test non-dictionary input
        with pytest.raises(ValueError, match='content_source must be a dictionary'):
            client._validate_content_source([])

        # Test missing retriever
        with pytest.raises(ValueError, match="content_source must include 'retriever'"):
            client._validate_content_source({})

        # Test invalid retriever type
        with pytest.raises(
            ValueError, match="content_source.retriever must include 'retrieverId'"
        ):
            client._validate_content_source({'retriever': 'not_a_dict'})

        # Test missing retrieverId
        with pytest.raises(
            ValueError, match="content_source.retriever must include 'retrieverId'"
        ):
            client._validate_content_source({'retriever': {}})

    def test_validate_max_results_invalid(self, client):
        """Test max_results validation with invalid values."""
        # Test non-integer input
        with pytest.raises(ValueError, match='max_results must be an integer'):
            client._validate_max_results('10')

        # Test out of range values
        with pytest.raises(ValueError, match='max_results must be between 1 and 100'):
            client._validate_max_results(0)
        with pytest.raises(ValueError, match='max_results must be between 1 and 100'):
            client._validate_max_results(101)

    def test_validate_string_safety(self, client):
        """Test string safety validation."""
        # Test valid strings
        client._validate_string_safety('normal text', 'test_param')
        client._validate_string_safety('MAC_ADDRESS', 'test_param')

        # Test command injection patterns
        dangerous_inputs = [
            'text; rm -rf /',
            'text && echo hack',
            'text || true',
            'text | grep secret',
            'text > file.txt',
            'text < input.txt',
            'text >> append.txt',
            'text << EOF',
            '$(command)',
            '`command`',
            '${PATH}',
            "eval('code')",
            "exec('code')",
            "system('command')",
        ]

        for dangerous_input in dangerous_inputs:
            with pytest.raises(ValueError, match='Invalid character/pattern detected'):
                client._validate_string_safety(dangerous_input, 'test_param')

        # Test excessive length
        long_string = 'a' * 1001
        with pytest.raises(ValueError, match='exceeds maximum length'):
            client._validate_string_safety(long_string, 'test_param')

    def test_validate_attribute_filter_security(self, client):
        """Test attribute filter security validation."""
        # Test dangerous patterns in attribute name
        with pytest.raises(ValueError, match='Invalid character/pattern detected'):
            client._validate_attribute_filter(
                {'attributeName': 'test; rm -rf /', 'attributeValue': {'StringValue': 'test'}}
            )

        # Test dangerous patterns in string value
        with pytest.raises(ValueError, match='Invalid character/pattern detected'):
            client._validate_attribute_filter(
                {'attributeName': 'test', 'attributeValue': {'StringValue': '$(command)'}}
            )

        # Test dangerous patterns in string list
        with pytest.raises(ValueError, match='Invalid character/pattern detected'):
            client._validate_attribute_filter(
                {
                    'attributeName': 'test',
                    'attributeValue': {'StringListValue': ['normal', '`command`']},
                }
            )

        # Test dangerous patterns in equals to
        with pytest.raises(ValueError, match='Invalid character/pattern detected'):
            client._validate_attribute_filter(
                {'equalsTo': {'name': 'test; rm -rf /', 'value': {'StringValue': 'test'}}}
            )

    def test_validate_required_params_security(self, client):
        """Test required parameters security validation."""
        # Test dangerous patterns in application_id
        with pytest.raises(ValueError, match='Invalid character/pattern detected'):
            client._validate_required_params('app-id; rm -rf /', 'test query')

        # Test dangerous patterns in query_text
        with pytest.raises(ValueError, match='Invalid character/pattern detected'):
            client._validate_required_params('app-id', 'query && echo hack')

        # Test excessive length in application_id
        with pytest.raises(ValueError, match='exceeds maximum length'):
            client._validate_required_params('a' * 1001, 'test query')

        # Test excessive length in query_text
        with pytest.raises(ValueError, match='exceeds maximum length'):
            client._validate_required_params('app-id', 'a' * 1001)

    def test_validate_required_params_invalid(self, client):
        """Test required parameters validation with invalid values."""
        # Test invalid application_id
        with pytest.raises(ValueError, match='application_id must be a non-empty string'):
            client._validate_required_params(None, 'test')
        with pytest.raises(ValueError, match='application_id must be a non-empty string'):
            client._validate_required_params('', 'test')

        # Test invalid query_text
        with pytest.raises(ValueError, match='query_text must be a non-empty string'):
            client._validate_required_params('test-app', None)
        with pytest.raises(ValueError, match='query_text must be a non-empty string'):
            client._validate_required_params('test-app', '')
        with pytest.raises(ValueError, match='query_text cannot be empty or only whitespace'):
            client._validate_required_params('test-app', '   ')

    def test_search_relevant_content_success(self, client, mock_boto3_session):
        """Test successful search_relevant_content call."""
        # Get the mocked session and client
        mock_session, mock_client = mock_boto3_session

        # Set up the mock response
        mock_response = {
            'relevantContent': [{'content': 'test content', 'documentId': 'doc-123'}],
            'nextToken': 'next-token',
        }

        # Configure the mock client to return our response
        client.client = mock_client
        mock_client.search_relevant_content.return_value = mock_response

        # Make the call
        response = client.search_relevant_content(
            application_id='12345678-1234-5678-1234-567812345678',
            query_text='test query',
            attribute_filter={'attributeName': 'test', 'attributeValue': {'StringValue': 'test'}},
            content_source={
                'sourceType': 'WORKSPACE',
                'retriever': {'retrieverId': '12345678-1234-5678-1234-567812345678'},
            },
            max_results=10,
            next_token='token',
        )

        # Verify the response
        assert response == mock_response

        # Verify the call was made with correct parameters
        mock_client.search_relevant_content.assert_called_once_with(
            applicationId='12345678-1234-5678-1234-567812345678',
            queryText='test query',
            attributeFilter={'attributeName': 'test', 'attributeValue': {'StringValue': 'test'}},
            contentSource={
                'sourceType': 'WORKSPACE',
                'retriever': {'retrieverId': '12345678-1234-5678-1234-567812345678'},
            },
            maxResults=10,
            nextToken='token',
        )

    def test_search_relevant_content_invalid_response(self, client, mock_boto3_session):
        """Test search_relevant_content with invalid response."""
        _, mock_client = mock_boto3_session

        # Configure mock to return empty response
        mock_client.search_relevant_content = Mock(return_value={})

        # Set client.client to our mock
        client.client = mock_client

        with pytest.raises(
            QBusinessClientError, match='Invalid response received from AWS Q Business'
        ):
            client.search_relevant_content(
                application_id='12345678-1234-5678-1234-567812345678',
                query_text='test query',
                content_source={
                    'retriever': {
                        # Use a proper 36-character UUID format for retrieverId
                        'retrieverId': '12345678-1234-5678-1234-567812345678'
                    }
                },
            )

        # Verify the mock was called with correct parameters
        mock_client.search_relevant_content.assert_called_once()

    def test_search_relevant_content_security(self, client, mock_boto3_session):
        """Test search_relevant_content security validation."""
        _, mock_client = mock_boto3_session
        client.client = mock_client

        # Test dangerous patterns in parameters
        with pytest.raises(QBusinessClientError, match='Invalid character/pattern detected'):
            client.search_relevant_content(
                application_id='app-id; rm -rf /', query_text='test query'
            )

        with pytest.raises(QBusinessClientError, match='Invalid character/pattern detected'):
            client.search_relevant_content(
                application_id='app-id', query_text='query && echo hack'
            )

    def test_search_relevant_content_client_error(self, client, mock_boto3_session):
        """Test search_relevant_content with ClientError."""
        _, mock_client = mock_boto3_session
        # Set client.client to our mock
        client.client = mock_client
        error_response = cast(
            Any,
            {
                'Error': {'Code': 'ValidationException', 'Message': 'Test error message'},
                'ResponseMetadata': {
                    'RequestId': 'test-request-id',
                    'HostId': 'test-host',
                    'HTTPStatusCode': 400,
                    'HTTPHeaders': {},
                    'RetryAttempts': 0,
                },
            },
        )
        mock_client.search_relevant_content = Mock(
            side_effect=ClientError(error_response, 'SearchRelevantContent')
        )

        with pytest.raises(QBusinessClientError, match='Validation error: Test error message'):
            client.search_relevant_content(
                application_id='12345678-1234-5678-1234-567812345678',
                query_text='test query',
                content_source={
                    'retriever': {
                        # Use a proper 36-character UUID format for retrieverId
                        'retrieverId': '12345678-1234-5678-1234-567812345678'
                    }
                },
            )

        # Verify the mock was called with correct parameters
        mock_client.search_relevant_content.assert_called_once()

    def test_search_relevant_content_unexpected_error(self, client, mock_boto3_session):
        """Test search_relevant_content with unexpected error."""
        _, mock_client = mock_boto3_session
        # Set client.client to our mock
        client.client = mock_client
        # Configure mock to raise an unexpected exception
        mock_client.search_relevant_content = Mock(side_effect=Exception('Unexpected test error'))
        with pytest.raises(QBusinessClientError, match='Unexpected error: Unexpected test error'):
            client.search_relevant_content(
                application_id='12345678-1234-5678-1234-567812345678',
                query_text='test query',
                content_source={
                    'retriever': {
                        # Use a proper 36-character UUID format for retrieverId
                        'retrieverId': '12345678-1234-5678-1234-567812345678'
                    }
                },
            )

        # Verify the mock was called with correct parameters
        mock_client.search_relevant_content.assert_called_once()

    def test_handle_client_error_mapping(self, client):
        """Test _handle_client_error with different error codes."""
        error_codes = {
            'AccessDeniedException': 'Access denied',
            'ValidationException': 'Validation error',
            'ThrottlingException': 'Request throttled',
            'InternalServerException': 'Internal server error',
            'ResourceNotFoundException': 'Resource not found',
            'UnknownException': 'AWS Q Business error',
        }

        for code, expected_prefix in error_codes.items():
            error_response = cast(
                Any,
                {
                    'Error': {'Code': code, 'Message': 'Test message'},
                    'ResponseMetadata': {
                        'RequestId': 'test-request-id',
                        'HostId': 'test-host',
                        'HTTPStatusCode': 400,
                        'HTTPHeaders': {},
                        'RetryAttempts': 0,
                    },
                },
            )
            error = ClientError(error_response, 'TestOperation')
            with pytest.raises(QBusinessClientError) as exc_info:
                client._handle_client_error(error, 'TestOperation')
            assert expected_prefix in str(exc_info.value)
            assert 'Test message' in str(exc_info.value)
