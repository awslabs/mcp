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
from awslabs.amazon_kendra_index_mcp_server.server import example_tool


@pytest.mark.asyncio
async def test_example_tool(mocker):
    """Test the example_tool function returns the expected response with mocked Kendra response."""
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
    result = await example_tool(test_query)

    # Assert
    assert result == expected_result
    mock_kendra_client.query.assert_called_once()


@pytest.mark.asyncio
async def test_example_tool_error_handling(mocker):
    """Test the example_tool function handles errors from Kendra client."""
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
    result = await example_tool(test_query)

    # Assert
    assert result == expected_error_response
    mock_kendra_client.query.assert_called_once()
