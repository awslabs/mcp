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
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch
from typing import Dict, Any, cast
from awslabs.amazon_qindex_mcp_server.clients import QBusinessClient, QBusinessClientError


class TestQBusinessClient:
    @pytest.fixture
    def client(self):
        return QBusinessClient(
            region_name='us-east-1',
            aws_access_key_id='test-key',
            aws_secret_access_key='test-secret', # pragma: allowlist secret
            aws_session_token='test-token'
        )

    @pytest.fixture
    def mock_boto3_session(self):
        """Create a mock boto3 session with proper parameter validation bypass"""
        with patch('boto3.Session') as mock_session:
            mock_client = Mock()
            # Prevent parameter validation from boto3
            mock_client.meta.events.register.return_value = None
            mock_session.return_value.client.return_value = mock_client
            yield mock_session, mock_client

    def test_init_with_credentials(self, mock_boto3_session):
        """Test client initialization with credentials"""
        mock_session, _ = mock_boto3_session
        client = QBusinessClient(
            region_name='us-east-1',
            aws_access_key_id='test-key',
            aws_secret_access_key='test-secret', # pragma: allowlist secret
            aws_session_token='test-token'
        )
        mock_session.assert_called_once_with(
            aws_access_key_id='test-key',
            aws_secret_access_key='test-secret', # pragma: allowlist secret
            aws_session_token='test-token',
            region_name='us-east-1'
        )

    def test_init_without_credentials(self, mock_boto3_session):
        """Test client initialization without credentials"""
        mock_session, _ = mock_boto3_session
        client = QBusinessClient(region_name='us-east-1')
        mock_session.assert_called_once_with(
            aws_access_key_id=None,
            aws_secret_access_key=None, # pragma: allowlist secret
            aws_session_token=None,
            region_name='us-east-1'
        )

    def test_search_relevant_content_success(self, client, mock_boto3_session):
        """Test successful search_relevant_content call"""
        # Get the mocked session and client
        mock_session, mock_client = mock_boto3_session

        # Set up the mock response
        mock_response = {
            'relevantContent': [
                {
                    'content': 'test content',
                    'documentId': 'doc-123'
                }
            ],
            'nextToken': 'next-token'
        }

        # Configure the mock client to return our response
        client.client = mock_client
        mock_client.search_relevant_content.return_value = mock_response

        # Make the call
        response = client.search_relevant_content(
            application_id='12345678-1234-5678-1234-567812345678',
            query_text='test query',
            attribute_filter={
                'equalsTo': {
                    'name': 'test',
                    'value': {'stringValue': 'test'}
                }
            },
            content_source={
                'retriever': {
                    'retrieverId': '12345678-1234-5678-1234-567812345678'
                }
            },
            max_results=10,
            next_token='token'
        )

        # Verify the response
        assert response == mock_response

        # Verify the call was made with correct parameters
        mock_client.search_relevant_content.assert_called_once_with(
            applicationId='12345678-1234-5678-1234-567812345678',
            queryText='test query',
            attributeFilter={
                'equalsTo': {
                    'name': 'test',
                    'value': {'stringValue': 'test'}
                }
            },
            contentSource={
                'retriever': {
                    'retrieverId': '12345678-1234-5678-1234-567812345678'
                }
            },
            maxResults=10,
            nextToken='token'
        )

    def test_search_relevant_content_invalid_response(self, client, mock_boto3_session):
        """Test search_relevant_content with invalid response"""
        _, mock_client = mock_boto3_session

        # Configure mock to return empty response
        mock_client.search_relevant_content = Mock(return_value={})

        # Set client.client to our mock
        client.client = mock_client

        with pytest.raises(QBusinessClientError, match='Invalid response received from AWS Q Business'):
            client.search_relevant_content(
                application_id='12345678-1234-5678-1234-567812345678',
                query_text='test query',
                content_source={
                    'retriever': {
                        # Use a proper 36-character UUID format for retrieverId
                        'retrieverId': '12345678-1234-5678-1234-567812345678'
                    }
                }
            )

        # Verify the mock was called with correct parameters
        mock_client.search_relevant_content.assert_called_once()

    def test_search_relevant_content_client_error(self, client, mock_boto3_session):
        """Test search_relevant_content with ClientError"""
        _, mock_client = mock_boto3_session
        
        # Set client.client to our mock
        client.client = mock_client

        error_response = cast(Any, {
            'Error': {
                'Code': 'ValidationException',
                'Message': 'Test error message'
            },
            'ResponseMetadata': {
                'RequestId': 'test-request-id',
                'HostId': 'test-host',
                'HTTPStatusCode': 400,
                'HTTPHeaders': {},
                'RetryAttempts': 0
            }
        })
        
        mock_client.search_relevant_content = Mock(side_effect=ClientError(
            error_response,
            'SearchRelevantContent'
        ))


        with pytest.raises(QBusinessClientError, match='Validation error: Test error message'):
            client.search_relevant_content(
                application_id='12345678-1234-5678-1234-567812345678',
                query_text='test query',
                content_source={
                    'retriever': {
                        # Use a proper 36-character UUID format for retrieverId
                        'retrieverId': '12345678-1234-5678-1234-567812345678'
                    }
                }
            )

        # Verify the mock was called with correct parameters
        mock_client.search_relevant_content.assert_called_once()

    def test_search_relevant_content_unexpected_error(self, client, mock_boto3_session):
        """Test search_relevant_content with unexpected error"""
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
                }
            )

        # Verify the mock was called with correct parameters
        mock_client.search_relevant_content.assert_called_once()

    def test_handle_client_error_mapping(self, client):
        """Test _handle_client_error with different error codes"""
        error_codes = {
            'AccessDeniedException': 'Access denied',
            'ValidationException': 'Validation error',
            'ThrottlingException': 'Request throttled',
            'InternalServerException': 'Internal server error',
            'ResourceNotFoundException': 'Resource not found',
            'UnknownException': 'AWS Q Business error'
        }

        for code, expected_prefix in error_codes.items():
            error_response = cast(Any, {
                'Error': {
                    'Code': code,
                    'Message': 'Test message'
                },
                'ResponseMetadata': {
                    'RequestId': 'test-request-id',
                    'HostId': 'test-host',
                    'HTTPStatusCode': 400,
                    'HTTPHeaders': {},
                    'RetryAttempts': 0
                }
            })
            error = ClientError(error_response, 'TestOperation')

            with pytest.raises(QBusinessClientError) as exc_info:
                client._handle_client_error(error, 'TestOperation')
            
            assert expected_prefix in str(exc_info.value)
            assert 'Test message' in str(exc_info.value)