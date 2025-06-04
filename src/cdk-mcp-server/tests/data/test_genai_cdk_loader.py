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

"""Tests for the GenAI CDK GitHub-based loader."""

import pytest
from awslabs.cdk_mcp_server.data.genai_cdk_loader import (
    extract_sections,
    fetch_bedrock_subdirectories,
    fetch_readme,
    fetch_repo_structure,
    get_section,
    list_available_constructs,
    list_sections,
)
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_fetch_readme():
    """Test fetching README content from GitHub."""
    # Create a test response
    test_content = '# Test README\n\nContent'

    # Mock the cache first to make sure no real HTTP request happens
    mock_cache = {}

    # Use monkeypatch to prevent actual HTTP requests
    with (
        patch('awslabs.cdk_mcp_server.data.genai_cdk_loader._readme_cache', mock_cache),
        patch(
            'awslabs.cdk_mcp_server.data.genai_cdk_loader.httpx.AsyncClient'
        ) as mock_client_factory,
    ):
        # Create a mock client and response
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = test_content

        # Set up the chain: AsyncClient() -> __aenter__() -> client -> get() -> response
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client_factory.return_value = mock_client

        # Call the function with our mocked HTTP client
        result = await fetch_readme('bedrock')

        # Verify that our mock was used and returned the expected content
        assert result['status'] == 'success'
        assert result['content'] == test_content
        assert 'bedrock' in result['path']

        # Verify the HTTP call was made to the expected URL
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args[0][0]
        assert 'README.md' in call_args
        assert 'bedrock' in call_args


@pytest.mark.asyncio
async def test_fetch_readme_error():
    """Test error handling when fetching README content fails."""
    # Create a mock response with 404 error
    mock_response = MagicMock()
    mock_response.status_code = 404

    # Set up an AsyncMock for the client
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    # Use contextlib to create a mock async context manager
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_client

    # Patch the AsyncClient to return our mock context manager
    with patch('httpx.AsyncClient', return_value=mock_context):
        result = await fetch_readme('bedrock', 'nonexistent')

        # Verify the result contains an error
        assert 'error' in result
        assert result.get('status_code') == 404


@pytest.mark.asyncio
async def test_extract_sections():
    """Test extracting sections from README content."""
    content = """# Main Title

Introduction paragraph

## Section One
Content for section one
More content

## Section Two
Content for section two

### Subsection
This is a subsection that shouldn't be captured as a top-level section

## Section Three
Final section content
"""

    sections = extract_sections(content)

    # Check that we got the expected sections
    assert len(sections) == 3
    assert 'Section One' in sections
    assert 'Section Two' in sections
    assert 'Section Three' in sections

    # Check that section content is extracted correctly
    assert 'Content for section one' in sections['Section One']
    assert 'Content for section two' in sections['Section Two']
    assert 'Final section content' in sections['Section Three']

    # Ensure section headers are included in content
    assert '## Section One' in sections['Section One']

    # Check subsection handling
    assert '### Subsection' in sections['Section Two']
    assert 'This is a subsection' in sections['Section Two']


@pytest.mark.asyncio
async def test_list_sections_success():
    """Test listing available sections successfully with GitHub-based approach."""
    # Create test content with sections
    test_content = """# Test README

    Introduction text

    ## Section One
    Content for section one

    ## Section Two
    Content for section two

    ## Section Three
    Content for section three
    """

    test_sections = {
        'Section One': '## Section One\nContent for section one',
        'Section Two': '## Section Two\nContent for section two',
        'Section Three': '## Section Three\nContent for section three',
    }

    # Mock both fetch_readme and extract_sections
    with (
        patch(
            'awslabs.cdk_mcp_server.data.genai_cdk_loader.fetch_readme', new=AsyncMock()
        ) as mock_fetch_readme,
        patch(
            'awslabs.cdk_mcp_server.data.genai_cdk_loader.extract_sections',
            return_value=test_sections,
        ) as mock_extract,
    ):
        # Setup the mock return value
        mock_fetch_readme.return_value = {'content': test_content, 'status': 'success'}

        # Test listing sections
        result = await list_sections('bedrock', 'agent')

        # Check that mock was called with correct arguments
        mock_fetch_readme.assert_called_with('bedrock', 'agent')
        mock_extract.assert_called_once_with(test_content)

        # Check result
        assert result['status'] == 'success'
        assert 'Section One' in result['sections']
        assert 'Section Two' in result['sections']
        assert 'Section Three' in result['sections']
        assert len(result['sections']) == 3


@pytest.mark.asyncio
async def test_list_sections_error():
    """Test listing sections when README fetch fails."""
    # Mock the cache to ensure clean test state
    mock_cache = {}

    with (
        patch('awslabs.cdk_mcp_server.data.genai_cdk_loader._sections_cache', mock_cache),
        patch(
            'awslabs.cdk_mcp_server.data.genai_cdk_loader.fetch_readme', new=AsyncMock()
        ) as mock_fetch_readme,
    ):
        # Setup mock to return an error
        mock_fetch_readme.return_value = {'error': 'Test error message', 'status': 'error'}

        # Call the function
        result = await list_sections('bedrock', 'agent')

        # Verify the implementation always returns a success result
        # with empty sections when fetch_readme has an error
        assert result['status'] == 'success'
        assert result['path'] == 'bedrock/agent'
        assert result['sections'] == []


@pytest.mark.asyncio
async def test_get_section_success():
    """Test getting a specific section from a README."""
    # Setup our test data
    test_sections = {'Test Section': '## Test Section\nThis is test content'}

    # Create the expected result
    expected_result = {
        'content': '## Test Section\nThis is test content',
        'section': 'Test Section',
        'path': 'bedrock/agent',
        'status': 'success',
    }

    # Mock the functions with a deeper inspection of the header name
    with (
        patch('awslabs.cdk_mcp_server.data.genai_cdk_loader._sections_cache', {}),
        patch(
            'awslabs.cdk_mcp_server.data.genai_cdk_loader.fetch_readme', new=AsyncMock()
        ) as mock_fetch_readme,
        patch(
            'awslabs.cdk_mcp_server.data.genai_cdk_loader.extract_sections',
            return_value=test_sections,
        ),
    ):
        # Set up the mock README result
        mock_fetch_readme.return_value = {
            'content': '# Test\n\n## Test Section\nThis is test content',
            'status': 'success',
        }

        # Force the case match in the test
        result = await get_section('bedrock', 'agent', 'Test Section')

        # Verify the result - this test checks the object-for-object matching
        # which is more strict than just comparing fields
        assert result == expected_result


@pytest.mark.asyncio
async def test_get_section_not_found():
    """Test when a section is not found."""
    # Setup test data
    test_sections = {'Test Section': '## Test Section\nThis is test content'}

    # Mock the functions
    with (
        patch(
            'awslabs.cdk_mcp_server.data.genai_cdk_loader.fetch_readme', new=AsyncMock()
        ) as mock_fetch_readme,
        patch(
            'awslabs.cdk_mcp_server.data.genai_cdk_loader.extract_sections',
            return_value=test_sections,
        ),
    ):
        mock_fetch_readme.return_value = {
            'content': '# Test\n\n## Test Section\nThis is test content',
            'status': 'success',
        }

        # Call the function with a non-existent section
        result = await get_section('bedrock', 'agent', 'nonexistent section')

        # Verify the result
        assert 'error' in result
        assert result['status'] == 'not_found'


@pytest.mark.asyncio
async def test_fetch_repo_structure():
    """Test fetching repository structure from GitHub."""
    # Create a mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            'name': 'bedrock',
            'type': 'dir',
            'path': 'src/cdk-lib/bedrock',
            'html_url': 'https://github.com/url',
        },
        {
            'name': 'opensearch',
            'type': 'dir',
            'path': 'src/cdk-lib/opensearch',
            'html_url': 'https://github.com/url',
        },
    ]

    # Set up an AsyncMock for the client
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    # Use contextlib to create a mock async context manager
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_client

    # Mock the fetch_readme function as well
    with (
        patch('httpx.AsyncClient', return_value=mock_context),
        patch(
            'awslabs.cdk_mcp_server.data.genai_cdk_loader.fetch_readme', new=AsyncMock()
        ) as mock_fetch_readme,
    ):
        mock_fetch_readme.return_value = {
            'content': '# Test\n\nDescription text',
            'status': 'success',
        }

        # Call the function
        result = await fetch_repo_structure()

        # Verify the result has construct types
        assert 'construct_types' in result
        assert len(result['construct_types']) > 0


@pytest.mark.asyncio
async def test_fetch_bedrock_subdirectories():
    """Test fetching bedrock subdirectories."""
    # Mock API response data from GitHub
    mock_dirs_response = [
        {
            'name': 'agents',
            'type': 'dir',
            'path': 'src/cdk-lib/bedrock/agents',
            'html_url': 'https://github.com/url',
        },
        {
            'name': 'kb',
            'type': 'dir',
            'path': 'src/cdk-lib/bedrock/kb',
            'html_url': 'https://github.com/url',
        },
    ]

    # Set up HTTP mock response for GitHub API
    mock_http_response = MagicMock()
    mock_http_response.status_code = 200
    mock_http_response.json.return_value = mock_dirs_response

    # Set up the HTTP client mock
    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_http_response

    # Create the async context manager mock
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_http_client

    # Mock README response for each directory
    mock_readme_response = {'content': '# Test Directory\n\nTest description', 'status': 'success'}

    # Apply the mocks
    with (
        patch('httpx.AsyncClient', return_value=mock_context),
        patch(
            'awslabs.cdk_mcp_server.data.genai_cdk_loader.fetch_readme',
            return_value=mock_readme_response,
            new_callable=AsyncMock,
        ),
    ):
        # Call the function
        result = await fetch_bedrock_subdirectories()

        # Verify API was called
        mock_http_client.get.assert_called_once()

        # Verify we have results
        assert len(result) == 2

        # Check that result subdirectories have expected fields
        assert all(key in result[0] for key in ['name', 'path', 'url', 'description'])


@pytest.mark.asyncio
async def test_list_available_constructs():
    """Test listing available constructs."""
    # Mock fetch_repo_structure
    with (
        patch(
            'awslabs.cdk_mcp_server.data.genai_cdk_loader.fetch_repo_structure', new=AsyncMock()
        ) as mock_fetch_structure,
        patch(
            'awslabs.cdk_mcp_server.data.genai_cdk_loader.fetch_readme', new=AsyncMock()
        ) as mock_fetch_readme,
        patch(
            'awslabs.cdk_mcp_server.data.genai_cdk_loader.extract_sections',
            return_value={'Section One': '## Section One\nContent'},
        ),
    ):
        # Setup the mock return values
        mock_fetch_structure.return_value = {
            'construct_types': {
                'bedrock': {
                    'name': 'Bedrock',
                    'description': 'Amazon Bedrock Constructs',
                    'path': 'src/cdk-lib/bedrock',
                    'url': 'https://github.com/url',
                    'subdirectories': [
                        {
                            'name': 'Agents',
                            'path': 'bedrock/agents',
                            'url': 'https://github.com/url',
                            'description': 'Agent Constructs',
                        }
                    ],
                }
            }
        }

        mock_fetch_readme.return_value = {
            'content': '# Test\n\n## Section One\nContent',
            'status': 'success',
        }

        # Call the function
        constructs = await list_available_constructs('bedrock')

        # Verify the result
        assert len(constructs) > 0
        assert any(c['name'] == 'Bedrock' and c['type'] == 'bedrock' for c in constructs)


@pytest.mark.asyncio
async def test_list_available_constructs_empty_result():
    """Test listing available constructs returns empty when error occurs."""
    # Mock fetch_repo_structure to return an error
    with patch(
        'awslabs.cdk_mcp_server.data.genai_cdk_loader.fetch_repo_structure', new=AsyncMock()
    ) as mock_fetch_structure:
        mock_fetch_structure.return_value = {'error': 'Test error'}

        # Call the function
        constructs = await list_available_constructs('bedrock')

        # Verify that an empty list is returned
        assert constructs == []
