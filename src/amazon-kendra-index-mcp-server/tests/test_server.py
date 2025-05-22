# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the amazon-kendra-index-mcp-server MCP Server."""

import pytest
from awslabs.amazon_kendra_index_mcp_server.server import (
    kendra_list_indexes_tool,
    kendra_query_tool,
)
from datetime import datetime


@pytest.mark.asyncio
async def test_kendra_query_tool(mocker):
    """Test the kendra_query_tool function returns the expected response with mocked Kendra response."""
    # Arrange
    test_query = 'test query'
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv('KENDRA_INDEX_ID', '123456789')
    # Mock the boto3 client and its query method
    mock_kendra_client = mocker.Mock()
    mock_kendra_response = {
        'TotalNumberOfResults': 2,
        'ResultItems': [
            {
                'Id': 'result-1',
                'Type': 'DOCUMENT',
                'DocumentTitle': {'Text': 'Test Document 1'},
                'DocumentURI': 'https://example.com/doc1',
                'ScoreAttributes': {'ScoreConfidence': 'HIGH'},
                'DocumentExcerpt': {'Text': 'This is an excerpt from document 1'},
            },
            {
                'Id': 'result-2',
                'Type': 'QUESTION_ANSWER',
                'DocumentTitle': {'Text': 'Test Document 2'},
                'DocumentURI': 'https://example.com/doc2',
                'ScoreAttributes': {'ScoreConfidence': 'MEDIUM'},
                'DocumentExcerpt': {'Text': 'This is an excerpt from document 2'},
                'AdditionalAttributes': [
                    {
                        'Key': 'AnswerText',
                        'Value': {'TextWithHighlightsValue': {'Text': 'This is the answer'}},
                    }
                ],
            },
        ],
    }

    mock_kendra_client.query.return_value = mock_kendra_response
    mocker.patch('boto3.client', return_value=mock_kendra_client)

    # Expected result based on the mock response
    expected_result = {
        'query': test_query,
        'total_results_count': 2,
        'results': [
            {
                'id': 'result-1',
                'type': 'DOCUMENT',
                'document_title': 'Test Document 1',
                'document_uri': 'https://example.com/doc1',
                'score': 'HIGH',
                'excerpt': 'This is an excerpt from document 1',
            },
            {
                'id': 'result-2',
                'type': 'QUESTION_ANSWER',
                'document_title': 'Test Document 2',
                'document_uri': 'https://example.com/doc2',
                'score': 'MEDIUM',
                'excerpt': 'This is an excerpt from document 2',
                'additional_attributes': [
                    {
                        'Key': 'AnswerText',
                        'Value': {'TextWithHighlightsValue': {'Text': 'This is the answer'}},
                    }
                ],
            },
        ],
    }

    # Act
    result = await kendra_query_tool(test_query)

    # Assert
    assert result == expected_result
    mock_kendra_client.query.assert_called_once()


@pytest.mark.asyncio
async def test_kendra_query_tool_error_handling(mocker):
    """Test the kendra_query_tool function handles errors from Kendra client."""
    # Arrange
    test_query = 'test query'

    # Mock boto3 client to raise an exception
    mock_kendra_client = mocker.Mock()
    mock_kendra_client.query.side_effect = Exception('Kendra service error')
    mocker.patch('boto3.client', return_value=mock_kendra_client)

    # Mock environment variable for kendra_index_id
    mocker.patch('os.getenv', return_value='mock-index-id')

    # Expected error response
    expected_error_response = {
        'error': 'Kendra service error',
        'query': test_query,
        'index_id': 'mock-index-id',
    }

    # Act
    result = await kendra_query_tool(test_query)

    # Assert
    assert result == expected_error_response
    mock_kendra_client.query.assert_called_once()


@pytest.mark.asyncio
async def test_kendra_list_indexes_tool(mocker):
    """Test the kendra_list_indexes_tool function returns the expected response with mocked Kendra response."""
    # Arrange
    test_region = 'us-west-2'
    created_at = datetime(2023, 1, 1, 12, 0, 0)
    updated_at = datetime(2023, 2, 1, 12, 0, 0)

    # Mock the boto3 client and its list_indices method
    mock_kendra_client = mocker.Mock()
    mock_kendra_response = {
        'IndexConfigurationSummaryItems': [
            {
                'Id': 'index-1',
                'Name': 'Test Index 1',
                'Status': 'ACTIVE',
                'CreatedAt': created_at,
                'UpdatedAt': updated_at,
                'Edition': 'DEVELOPER_EDITION',
            },
            {
                'Id': 'index-2',
                'Name': 'Test Index 2',
                'Status': 'UPDATING',
                'CreatedAt': created_at,
                'UpdatedAt': updated_at,
                'Edition': 'ENTERPRISE_EDITION',
            },
        ]
    }

    mock_kendra_client.list_indices.return_value = mock_kendra_response
    mocker.patch('boto3.client', return_value=mock_kendra_client)

    # Expected result based on the mock response
    expected_result = {
        'region': test_region,
        'count': 2,
        'indexes': [
            {
                'id': 'index-1',
                'name': 'Test Index 1',
                'status': 'ACTIVE',
                'created_at': created_at.isoformat(),
                'updated_at': updated_at.isoformat(),
                'edition': 'DEVELOPER_EDITION',
            },
            {
                'id': 'index-2',
                'name': 'Test Index 2',
                'status': 'UPDATING',
                'created_at': created_at.isoformat(),
                'updated_at': updated_at.isoformat(),
                'edition': 'ENTERPRISE_EDITION',
            },
        ],
    }

    # Act
    result = await kendra_list_indexes_tool(region=test_region)

    # Assert
    assert result == expected_result
    mock_kendra_client.list_indices.assert_called_once()


@pytest.mark.asyncio
async def test_kendra_list_indexes_tool_pagination(mocker):
    """Test the kendra_list_indexes_tool function handles pagination correctly."""
    # Arrange
    test_region = 'us-west-2'
    created_at = datetime(2023, 1, 1, 12, 0, 0)
    updated_at = datetime(2023, 2, 1, 12, 0, 0)

    # Mock the boto3 client and its list_indices method with pagination
    mock_kendra_client = mocker.Mock()

    # First response with NextToken
    first_response = {
        'IndexConfigurationSummaryItems': [
            {
                'Id': 'index-1',
                'Name': 'Test Index 1',
                'Status': 'ACTIVE',
                'CreatedAt': created_at,
                'UpdatedAt': updated_at,
                'Edition': 'DEVELOPER_EDITION',
            }
        ],
        'NextToken': 'next-page-token',
    }

    # Second response without NextToken
    second_response = {
        'IndexConfigurationSummaryItems': [
            {
                'Id': 'index-2',
                'Name': 'Test Index 2',
                'Status': 'UPDATING',
                'CreatedAt': created_at,
                'UpdatedAt': updated_at,
                'Edition': 'ENTERPRISE_EDITION',
            }
        ]
    }

    # Configure mock to return different responses
    mock_kendra_client.list_indices.side_effect = [first_response, second_response]
    mocker.patch('boto3.client', return_value=mock_kendra_client)

    # Expected result combining both responses
    expected_result = {
        'region': test_region,
        'count': 2,
        'indexes': [
            {
                'id': 'index-1',
                'name': 'Test Index 1',
                'status': 'ACTIVE',
                'created_at': created_at.isoformat(),
                'updated_at': updated_at.isoformat(),
                'edition': 'DEVELOPER_EDITION',
            },
            {
                'id': 'index-2',
                'name': 'Test Index 2',
                'status': 'UPDATING',
                'created_at': created_at.isoformat(),
                'updated_at': updated_at.isoformat(),
                'edition': 'ENTERPRISE_EDITION',
            },
        ],
    }

    # Act
    result = await kendra_list_indexes_tool(region=test_region)

    # Assert
    assert result == expected_result
    assert mock_kendra_client.list_indices.call_count == 2
    # First call without NextToken
    mock_kendra_client.list_indices.assert_any_call()
    # Second call with NextToken
    mock_kendra_client.list_indices.assert_any_call(NextToken='next-page-token')


@pytest.mark.asyncio
async def test_lkendra_list_indexes_tool_error_handling(mocker):
    """Test the kendra_list_indexes_tool function handles errors from Kendra client."""
    # Arrange
    test_region = 'us-west-2'

    # Mock boto3 client to raise an exception
    mock_kendra_client = mocker.Mock()
    mock_kendra_client.list_indices.side_effect = Exception('Kendra service error')
    mocker.patch('boto3.client', return_value=mock_kendra_client)

    # Expected error response
    expected_error_response = {
        'error': 'Kendra service error',
        'region': test_region,
    }

    # Act
    result = await kendra_list_indexes_tool(region=test_region)

    # Assert
    assert result == expected_error_response
    mock_kendra_client.list_indices.assert_called_once()
