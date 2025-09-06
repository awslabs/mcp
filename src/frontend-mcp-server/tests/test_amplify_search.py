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
"""Tests for the SearchAmplifyGen2Docs MCP tool."""

import pytest
from unittest.mock import patch
from awslabs.frontend_mcp_server.server import search_amplify_gen2_documentation_tool


@pytest.fixture
def mock_search_results():
    """Mock search results for testing."""
    return [
        {
            "title": "Authentication Setup",
            "path": "docs/authentication.md",
            "url": "https://github.com/aws-amplify/amplify-backend/blob/main/docs/authentication.md",
            "relevance_score": 0.95,
            "content_preview": "Setting up authentication with defineAuth..."
        },
        {
            "title": "Data Modeling",
            "path": "docs/data.md", 
            "url": "https://github.com/aws-amplify/amplify-backend/blob/main/docs/data.md",
            "relevance_score": 0.87,
            "content_preview": "Creating data models with defineData..."
        }
    ]

@pytest.mark.asyncio
@patch('awslabs.frontend_mcp_server.server.search_amplify_documentation')
async def test_search_amplify_gen2_docs_basic_query(mock_search, mock_search_results):
    """Test SearchAmplifyGen2Docs tool with basic authentication query."""
    # Arrange
    mock_search.return_value = mock_search_results
    query = "authentication"
    
    # Act
    result = await search_amplify_gen2_documentation_tool(query)
    
    # Assert
    mock_search.assert_called_once_with("authentication", 10)
    assert "Found 2 results for 'authentication'" in result
    assert "Authentication Setup" in result
    assert "Data Modeling" in result

@pytest.mark.asyncio
@patch('awslabs.frontend_mcp_server.server.search_amplify_documentation')
async def test_search_amplify_gen2_docs_with_limit(mock_search, mock_search_results):
    """Test SearchAmplifyGen2Docs tool with custom limit."""
    # Arrange
    mock_search.return_value = mock_search_results[:1]  # Return only first result
    query = "data modeling"
    limit = 1
    
    # Act
    result = await search_amplify_gen2_documentation_tool(query, limit)
    
    # Assert
    mock_search.assert_called_once_with("data modeling", 1)
    assert "Found 1 results for 'data modeling'" in result
    assert "Authentication Setup" in result

@pytest.mark.asyncio
@patch('awslabs.frontend_mcp_server.server.search_amplify_documentation')
async def test_search_amplify_gen2_docs_no_results(mock_search):
    """Test SearchAmplifyGen2Docs tool with no results."""
    # Arrange
    mock_search.return_value = []
    query = "nonexistent"
    
    # Act
    result = await search_amplify_gen2_documentation_tool(query)
    
    # Assert
    mock_search.assert_called_once_with("nonexistent", 10)
    assert "No documentation found for query: 'nonexistent'" in result

@pytest.mark.asyncio
@patch('awslabs.frontend_mcp_server.server.search_amplify_documentation')
async def test_search_amplify_gen2_docs_complex_query(mock_search, mock_search_results):
    """Test SearchAmplifyGen2Docs tool with complex query."""
    # Arrange
    mock_search.return_value = mock_search_results
    query = "authentication with email and password login"
    
    # Act
    result = await search_amplify_gen2_documentation_tool(query)
    
    # Assert
    mock_search.assert_called_once_with("authentication with email and password login", 10)
    assert "Found 2 results" in result
    assert "0.95" in result  # Check relevance score is displayed

@pytest.mark.asyncio
@patch('awslabs.frontend_mcp_server.server.search_amplify_documentation')
async def test_search_amplify_gen2_docs_exception_handling(mock_search):
    """Test SearchAmplifyGen2Docs tool handles exceptions gracefully."""
    # Arrange
    mock_search.side_effect = Exception("Network error")
    query = "authentication"
    
    # Act & Assert
    with pytest.raises(Exception, match="Network error"):
        await search_amplify_gen2_documentation_tool(query)
