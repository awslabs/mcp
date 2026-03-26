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
"""Tests for the frontend MCP Server."""

import pytest
import warnings
from awslabs.frontend_mcp_server.server import DEPRECATION_NOTICE, get_react_docs_by_topic, main
from unittest.mock import patch


@pytest.mark.asyncio
@patch('awslabs.frontend_mcp_server.server.load_markdown_file')
async def test_get_react_docs_by_topic_essential_knowledge(mock_load_markdown):
    """Test the get_react_docs_by_topic tool returns correct content for essential-knowledge topic."""
    # Arrange
    mock_load_markdown.return_value = 'Essential knowledge content'

    # Act
    result = await get_react_docs_by_topic('essential-knowledge')

    # Assert
    mock_load_markdown.assert_called_once_with('essential-knowledge.md')
    assert result == 'Essential knowledge content'


@pytest.mark.asyncio
@patch('awslabs.frontend_mcp_server.server.load_markdown_file')
async def test_get_react_docs_by_topic_troubleshooting(mock_load_markdown):
    """Test the get_react_docs_by_topic tool returns correct content for troubleshooting topic."""
    # Arrange
    mock_load_markdown.return_value = 'Troubleshooting content'

    # Act
    result = await get_react_docs_by_topic('troubleshooting')

    # Assert
    mock_load_markdown.assert_called_once_with('troubleshooting.md')
    assert result == 'Troubleshooting content'


@pytest.mark.asyncio
async def test_get_react_docs_by_topic_invalid():
    """Test the get_react_docs_by_topic tool raises ValueError for invalid topic."""
    # Act & Assert
    with pytest.raises(ValueError, match='Invalid topic:'):
        await get_react_docs_by_topic('invalid-topic')


@patch('awslabs.frontend_mcp_server.server.mcp')
def test_main_emits_deprecation_warning(mock_mcp):
    """Test that main() emits a FutureWarning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        main()
        future_warnings = [x for x in w if issubclass(x.category, FutureWarning)]
        assert len(future_warnings) == 1
        assert DEPRECATION_NOTICE in str(future_warnings[0].message)
    mock_mcp.run.assert_called_once()
