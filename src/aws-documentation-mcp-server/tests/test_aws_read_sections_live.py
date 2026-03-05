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
"""Live test for the read_sections tool in the AWS Documentation MCP server."""

import pytest
from awslabs.aws_documentation_mcp_server.server_aws import (
    read_sections as read_sections_global,
)
from tests.constants import TEST_USER_AGENT
from unittest.mock import patch


class MockContext:
    """Mock context for testing."""

    async def error(self, message):
        """Mock error method."""
        print(f'Error: {message}')


@pytest.mark.asyncio
@pytest.mark.live
async def test_read_sections_live_basic():
    """Test basic section extraction from stable AWS documentation URL."""
    url = 'https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html'
    section_titles = ['General purpose buckets naming rules']
    ctx = MockContext()

    with patch(
        'awslabs.aws_documentation_mcp_server.server_aws.DEFAULT_USER_AGENT',
        TEST_USER_AGENT,
    ):
        result = await read_sections_global(ctx, url=url, section_titles=section_titles)

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

        assert 'general purpose buckets naming rules' in result.lower()

        assert 'Error extracting sections:' not in result, 'Found error indicator in the result'


@pytest.mark.asyncio
@pytest.mark.live
async def test_read_sections_live_multiple_sections():
    """Test extracting multiple sections from a comprehensive AWS documentation page."""
    # Use S3 bucket naming rules documentation with multiple sections
    url = 'https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html'
    section_titles = [
        'General purpose buckets naming rules',
        'Example general purpose bucket names',
    ]
    ctx = MockContext()

    with patch(
        'awslabs.aws_documentation_mcp_server.server_aws.DEFAULT_USER_AGENT',
        TEST_USER_AGENT,
    ):
        result = await read_sections_global(ctx, url=url, section_titles=section_titles)

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

        assert 'general purpose buckets naming rules' in result.lower()
        assert 'example general purpose bucket names' in result.lower()

        assert 'Error extracting sections:' not in result, 'Found error indicator in the result'


@pytest.mark.asyncio
@pytest.mark.live
async def test_read_sections_live_missing_sections():
    """Test graceful handling when some requested sections don't exist."""
    url = 'https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html'
    section_titles = [
        'General purpose buckets naming rules',  # This should exist
        'Nonexistent Section Title',  # This should not exist
        'Another Missing Section',  # This should also not exist
    ]
    ctx = MockContext()

    with patch(
        'awslabs.aws_documentation_mcp_server.server_aws.DEFAULT_USER_AGENT',
        TEST_USER_AGENT,
    ):
        result = await read_sections_global(ctx, url=url, section_titles=section_titles)

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

        assert 'general purpose buckets naming rules' in result.lower()

        expected_missing_note = '> **Note**: The following requested sections were not found: "Nonexistent Section Title", "Another Missing Section"'
        assert expected_missing_note in result


@pytest.mark.asyncio
@pytest.mark.live
async def test_read_sections_live_case_insensitive():
    """Test case-insensitive section matching against real documentation."""
    url = 'https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html'
    # Use different capitalization than the actual heading
    section_titles = [
        'GENERAL PURPOSE BUCKETS NAMING RULES'
    ]  # Should match despite case difference
    ctx = MockContext()

    with patch(
        'awslabs.aws_documentation_mcp_server.server_aws.DEFAULT_USER_AGENT',
        TEST_USER_AGENT,
    ):
        result = await read_sections_global(ctx, url=url, section_titles=section_titles)

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

        assert 'general purpose buckets naming rules' in result.lower()

        assert 'Error extracting sections:' not in result, 'Found error indicator in the result'


@pytest.mark.asyncio
@pytest.mark.live
async def test_read_sections_live_whitespace_normalization():
    """Whitespace normalization with real documentation."""
    url = 'https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html'
    # Test with extra whitespace that should still match "General purpose buckets naming rules"
    section_titles = ['  General   purpose buckets naming rules  \n']
    ctx = MockContext()

    with patch(
        'awslabs.aws_documentation_mcp_server.server_aws.DEFAULT_USER_AGENT',
        TEST_USER_AGENT,
    ):
        result = await read_sections_global(ctx, url=url, section_titles=section_titles)

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

        assert 'general purpose buckets naming rules' in result.lower()
        assert 'Error extracting sections:' not in result, 'Found error indicator in the result'


@pytest.mark.asyncio
@pytest.mark.live
async def test_read_sections_live_all_sections_fail():
    """Test that when all sections fail to match, ValueError is raised with helpful message."""
    url = 'https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html'
    # Use section titles that definitely don't exist on this page
    section_titles = [
        'Completely Nonexistent Section',
        'Another Missing Section That Definitely Does Not Exist',
        'Third Fake Section Name',
    ]
    ctx = MockContext()

    with patch(
        'awslabs.aws_documentation_mcp_server.server_aws.DEFAULT_USER_AGENT',
        TEST_USER_AGENT,
    ):
        with pytest.raises(ValueError) as exc_info:
            await read_sections_global(ctx, url=url, section_titles=section_titles)

        error_message = str(exc_info.value)
        assert 'No matching sections were found:' in error_message
        assert 'Available sections:' in error_message
        assert 'use the read_documentation tool instead' in error_message
