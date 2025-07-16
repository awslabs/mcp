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

"""Tests for the MSK documentation resources."""

import json
import pytest

# Import the module instead of the functions directly
from awslabs.aws_msk_mcp_server.resources.documentation import resources
from unittest.mock import MagicMock, patch


class TestMSKDocumentationResources:
    """Tests for the MSK documentation resources."""

    @pytest.mark.asyncio
    async def test_msk_documentation_index(self):
        """Test the msk_documentation_index function."""
        # Arrange
        # Create a mock MCP server
        mock_mcp = MagicMock()
        resource_decorator = mock_mcp.resource.return_value

        # Register the resources with our mock
        await resources.register_module(mock_mcp)

        # Get the decorated function (first call to mock_mcp.resource)
        msk_documentation_index_func = resource_decorator.call_args_list[0][0][0]

        # Act
        result = await msk_documentation_index_func()
        result_json = json.loads(result)

        # Assert
        assert 'resources' in result_json
        assert len(result_json['resources']) == 2

        # Check first resource
        assert result_json['resources'][0]['uri'] == 'resource://msk-documentation/developer-guide'
        assert result_json['resources'][0]['name'] == 'Amazon MSK Developer Guide'

        # Check second resource
        assert (
            result_json['resources'][1]['uri']
            == 'resource://msk-documentation/developer-guide/toc'
        )
        assert (
            result_json['resources'][1]['name'] == 'Amazon MSK Developer Guide Table of Contents'
        )

    @pytest.mark.asyncio
    @patch('awslabs.aws_msk_mcp_server.resources.documentation.resources.get_pdf_content')
    @patch('awslabs.aws_msk_mcp_server.resources.documentation.resources.extract_pdf_content')
    async def test_msk_developer_guide_success(
        self, mock_extract_pdf_content, mock_get_pdf_content
    ):
        """Test the msk_developer_guide function with successful PDF processing."""
        # Arrange
        # Create a mock MCP server
        mock_mcp = MagicMock()
        resource_decorator = mock_mcp.resource.return_value

        # Register the resources with our mock
        await resources.register_module(mock_mcp)

        # Get the decorated function (second call to mock_mcp.resource)
        msk_developer_guide_func = resource_decorator.call_args_list[1][0][0]

        mock_pdf_content = b'mock pdf content'
        mock_get_pdf_content.return_value = mock_pdf_content

        mock_content_result = {
            'content': 'Mock PDF content extracted',
            'pagination': {
                'start_page': 1,
                'end_page': 5,
                'total_pages': 100,
                'has_more': True,
            },
        }
        mock_extract_pdf_content.return_value = mock_content_result

        # Act
        result = await msk_developer_guide_func(start_page=1, end_page=5)
        result_json = json.loads(result)

        # Assert
        mock_get_pdf_content.assert_called_once_with('developer-guide')
        mock_extract_pdf_content.assert_called_once_with(mock_pdf_content, 1, 5)

        assert 'title' in result_json
        assert 'source_url' in result_json
        assert 'content' in result_json
        assert 'pagination' in result_json
        assert result_json['content'] == 'Mock PDF content extracted'
        assert result_json['pagination']['start_page'] == 1
        assert result_json['pagination']['end_page'] == 5

    @pytest.mark.asyncio
    @patch('awslabs.aws_msk_mcp_server.resources.documentation.resources.get_pdf_content')
    async def test_msk_developer_guide_error(self, mock_get_pdf_content):
        """Test the msk_developer_guide function when PDF processing fails."""
        # Arrange
        # Create a mock MCP server
        mock_mcp = MagicMock()
        resource_decorator = mock_mcp.resource.return_value

        # Register the resources with our mock
        await resources.register_module(mock_mcp)

        # Get the decorated function (second call to mock_mcp.resource)
        msk_developer_guide_func = resource_decorator.call_args_list[1][0][0]

        mock_get_pdf_content.side_effect = Exception('PDF processing failed')

        # Act
        result = await msk_developer_guide_func()
        result_json = json.loads(result)

        # Assert
        assert 'error' in result_json
        assert 'Failed to process PDF resource' in result_json['error']
        assert result_json['content'] is None

    @pytest.mark.asyncio
    @patch('awslabs.aws_msk_mcp_server.resources.documentation.resources.get_pdf_content')
    @patch('awslabs.aws_msk_mcp_server.resources.documentation.resources.extract_pdf_toc')
    async def test_msk_developer_guide_toc_success(
        self, mock_extract_pdf_toc, mock_get_pdf_content
    ):
        """Test the msk_developer_guide_toc function with successful TOC extraction."""
        # Arrange
        # Create a mock MCP server
        mock_mcp = MagicMock()
        resource_decorator = mock_mcp.resource.return_value

        # Register the resources with our mock
        await resources.register_module(mock_mcp)

        # Get the decorated function (third call to mock_mcp.resource)
        msk_developer_guide_toc_func = resource_decorator.call_args_list[2][0][0]

        mock_pdf_content = b'mock pdf content'
        mock_get_pdf_content.return_value = mock_pdf_content

        mock_toc = [
            {'title': 'Introduction', 'page': 1},
            {'title': 'Getting Started', 'page': 5},
            {'title': 'Advanced Topics', 'page': 20},
        ]
        mock_extract_pdf_toc.return_value = mock_toc

        # Act
        result = await msk_developer_guide_toc_func()
        result_json = json.loads(result)

        # Assert
        mock_get_pdf_content.assert_called_once_with('developer-guide')
        mock_extract_pdf_toc.assert_called_once_with(mock_pdf_content)

        assert 'title' in result_json
        assert 'source_url' in result_json
        assert 'toc' in result_json
        assert len(result_json['toc']) == 3
        assert result_json['toc'][0]['title'] == 'Introduction'
        assert result_json['toc'][0]['page'] == 1

    @pytest.mark.asyncio
    @patch('awslabs.aws_msk_mcp_server.resources.documentation.resources.get_pdf_content')
    async def test_msk_developer_guide_toc_error(self, mock_get_pdf_content):
        """Test the msk_developer_guide_toc function when TOC extraction fails."""
        # Arrange
        # Create a mock MCP server
        mock_mcp = MagicMock()
        resource_decorator = mock_mcp.resource.return_value

        # Register the resources with our mock
        await resources.register_module(mock_mcp)

        # Get the decorated function (third call to mock_mcp.resource)
        msk_developer_guide_toc_func = resource_decorator.call_args_list[2][0][0]

        mock_get_pdf_content.side_effect = Exception('TOC extraction failed')

        # Act
        result = await msk_developer_guide_toc_func()
        result_json = json.loads(result)

        # Assert
        assert 'error' in result_json
        assert 'Failed to process PDF TOC' in result_json['error']
        assert result_json['toc'] == []
