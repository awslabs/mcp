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

"""Unit tests for the resources/dev_guide.py module."""

import json
import pytest
import unittest
from awslabs.aws_msk_mcp_server.resources.dev_guide import register_module
from awslabs.aws_msk_mcp_server.resources.pdf_utils import PDF_RESOURCES
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
class TestDevGuide:
    """Tests for the dev_guide.py module."""

    async def test_register_module(self):
        """Test that register_module registers the expected resources."""
        # Create a mock MCP instance
        mock_mcp = MagicMock()
        mock_resource_decorator = MagicMock()
        mock_mcp.resource.return_value = mock_resource_decorator

        # Call the function under test
        await register_module(mock_mcp)

        # Verify that mcp.resource was called twice (once for each resource)
        assert mock_mcp.resource.call_count == 2

        # Verify the first resource registration (msk_developer_guide)
        first_call_args = mock_mcp.resource.call_args_list[0][1]
        assert (
            first_call_args['uri']
            == 'resource://msk-documentation/developer-guide/{start_page}/{end_page}'
        )
        assert first_call_args['name'] == 'MSKDeveloperGuide'
        assert first_call_args['mime_type'] == 'application/json'

        # Verify the second resource registration (msk_developer_guide_toc)
        second_call_args = mock_mcp.resource.call_args_list[1][1]
        assert second_call_args['uri'] == 'resource://msk-documentation/developer-guide'
        assert second_call_args['name'] == 'MSKDeveloperGuideTOC'
        assert second_call_args['mime_type'] == 'application/json'

    async def test_msk_developer_guide_success(self):
        """Test the msk_developer_guide resource function with successful PDF retrieval."""
        # Create a mock MCP instance
        mock_mcp = MagicMock()
        mock_resource_decorator = MagicMock()
        mock_mcp.resource.return_value = mock_resource_decorator

        # Mock PDF content and extraction
        mock_pdf_content = b'mock pdf content'
        mock_content_result = {
            'content': 'Mock extracted content',
            'pagination': {'start_page': 1, 'end_page': 5, 'total_pages': 100, 'has_more': True},
        }

        # Call register_module to get the resource functions
        with (
            patch(
                'awslabs.aws_msk_mcp_server.resources.dev_guide.get_pdf_content',
                new_callable=AsyncMock,
            ) as mock_get_pdf_content,
            patch(
                'awslabs.aws_msk_mcp_server.resources.dev_guide.extract_pdf_content'
            ) as mock_extract_pdf_content,
        ):
            mock_get_pdf_content.return_value = mock_pdf_content
            mock_extract_pdf_content.return_value = mock_content_result

            await register_module(mock_mcp)

            # Extract the msk_developer_guide function
            msk_developer_guide_func = mock_resource_decorator.call_args_list[0][0][0]

            # Call the function with parameters
            start_page = 1
            end_page = 5
            result_json = await msk_developer_guide_func(start_page, end_page)

            # Parse the JSON result
            result = json.loads(result_json)

            # Verify the result
            assert result['title'] == PDF_RESOURCES['developer-guide']['title']
            assert result['source_url'] == PDF_RESOURCES['developer-guide']['url']
            assert result['content'] == mock_content_result['content']
            assert result['pagination'] == mock_content_result['pagination']

            # Verify the mocked functions were called correctly
            mock_get_pdf_content.assert_called_once_with('developer-guide')
            mock_extract_pdf_content.assert_called_once_with(
                mock_pdf_content, start_page, end_page
            )

    async def test_msk_developer_guide_error(self):
        """Test the msk_developer_guide resource function with an error during PDF retrieval."""
        # Create a mock MCP instance
        mock_mcp = MagicMock()
        mock_resource_decorator = MagicMock()
        mock_mcp.resource.return_value = mock_resource_decorator

        # Call register_module to get the resource functions
        with patch(
            'awslabs.aws_msk_mcp_server.resources.dev_guide.get_pdf_content',
            new_callable=AsyncMock,
        ) as mock_get_pdf_content:
            # Mock an exception during PDF retrieval
            mock_get_pdf_content.side_effect = Exception('Failed to retrieve PDF')

            await register_module(mock_mcp)

            # Extract the msk_developer_guide function
            msk_developer_guide_func = mock_resource_decorator.call_args_list[0][0][0]

            # Call the function
            result_json = await msk_developer_guide_func()

            # Parse the JSON result
            result = json.loads(result_json)

            # Verify the result contains an error message
            assert 'error' in result
            assert result['content'] is None
            assert 'Failed to retrieve PDF' in result['error']

    async def test_msk_developer_guide_toc_success(self):
        """Test the msk_developer_guide_toc resource function with successful TOC extraction."""
        # Create a mock MCP instance
        mock_mcp = MagicMock()
        mock_resource_decorator = MagicMock()
        mock_mcp.resource.return_value = mock_resource_decorator

        # Mock PDF content and TOC extraction
        mock_pdf_content = b'mock pdf content'
        mock_toc = [
            {'title': 'Chapter 1', 'page': 10},
            {'title': 'Chapter 2', 'page': 20},
            {'title': 'Chapter 3', 'page': 30},
        ]

        # Call register_module to get the resource functions
        with (
            patch(
                'awslabs.aws_msk_mcp_server.resources.dev_guide.get_pdf_content',
                new_callable=AsyncMock,
            ) as mock_get_pdf_content,
            patch(
                'awslabs.aws_msk_mcp_server.resources.dev_guide.extract_pdf_toc'
            ) as mock_extract_pdf_toc,
        ):
            mock_get_pdf_content.return_value = mock_pdf_content
            mock_extract_pdf_toc.return_value = mock_toc

            await register_module(mock_mcp)

            # Extract the msk_developer_guide_toc function
            msk_developer_guide_toc_func = mock_resource_decorator.call_args_list[1][0][0]

            # Call the function
            result_json = await msk_developer_guide_toc_func()

            # Parse the JSON result
            result = json.loads(result_json)

            # Verify the result
            assert result['title'] == PDF_RESOURCES['developer-guide']['title']
            assert result['source_url'] == PDF_RESOURCES['developer-guide']['url']
            assert result['toc'] == mock_toc

            # Verify the mocked functions were called correctly
            mock_get_pdf_content.assert_called_once_with('developer-guide')
            mock_extract_pdf_toc.assert_called_once_with(mock_pdf_content)

    async def test_msk_developer_guide_toc_error(self):
        """Test the msk_developer_guide_toc resource function with an error during TOC extraction."""
        # Create a mock MCP instance
        mock_mcp = MagicMock()
        mock_resource_decorator = MagicMock()
        mock_mcp.resource.return_value = mock_resource_decorator

        # Call register_module to get the resource functions
        with patch(
            'awslabs.aws_msk_mcp_server.resources.dev_guide.get_pdf_content',
            new_callable=AsyncMock,
        ) as mock_get_pdf_content:
            # Mock an exception during PDF retrieval
            mock_get_pdf_content.side_effect = Exception('Failed to retrieve PDF')

            await register_module(mock_mcp)

            # Extract the msk_developer_guide_toc function
            msk_developer_guide_toc_func = mock_resource_decorator.call_args_list[1][0][0]

            # Call the function
            result_json = await msk_developer_guide_toc_func()

            # Parse the JSON result
            result = json.loads(result_json)

            # Verify the result contains an error message
            assert 'error' in result
            assert result['toc'] == []
            assert 'Failed to retrieve PDF' in result['error']


if __name__ == '__main__':
    unittest.main()
