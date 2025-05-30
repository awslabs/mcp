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
"""Live test for the read_documentation tool in the AWS China Documentation MCP server."""

import pytest
from awslabs.aws_cn_documentation_mcp_server.server import read_documentation


class MockContext:
    """Mock context for testing."""

    async def error(self, message):
        """Mock error method."""
        print(f'Error: {message}')


@pytest.mark.asyncio
@pytest.mark.live
async def test_read_documentation_live():
    """Test that read_documentation can fetch real AWS documentation."""
    # Use a stable AWS documentation URL that's unlikely to change
    url = 'https://docs.amazonaws.cn/en_us/AmazonS3/latest/userguide/bucketnamingrules.html'
    ctx = MockContext()

    # Call the tool
    result = await read_documentation(ctx, url=url, max_length=5000, start_index=0)

    # Verify the result
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0

    # Check that the result contains the URL
    assert url in result

    # Check for expected content in the S3 bucket naming rules page
    expected_content_markers = [
        'bucket naming rules',
        'S3',
        'Amazon',
        'naming',
        'rules',
    ]

    for marker in expected_content_markers:
        assert marker.lower() in result.lower(), f"Expected to find '{marker}' in the result"

    # Check that the content is properly formatted
    assert 'AWS China Documentation from' in result

    # Check that the result doesn't contain error messages
    error_indicators = ['<e>Error', 'Failed to fetch']
    for indicator in error_indicators:
        assert indicator not in result, f"Found error indicator '{indicator}' in the result"

    # Print a sample of the result for debugging (will show in pytest output with -v flag)
    print('\nReceived documentation content (first 300 chars):')
    print(f'{result[:300]}...')


@pytest.mark.asyncio
@pytest.mark.live
async def test_read_documentation_pagination_live():
    """Test that read_documentation pagination works correctly."""
    # Use a stable AWS documentation URL that's likely to have substantial content
    url = 'https://docs.amazonaws.cn/en_us/AmazonS3/latest/userguide/Welcome.html'
    ctx = MockContext()

    # Create parameters for the tool with a small max_length to force pagination
    small_max_length = 1000

    # Call the tool for the first page
    first_page = await read_documentation(ctx, url=url, max_length=small_max_length, start_index=0)

    # Verify the first page
    assert first_page is not None
    assert isinstance(first_page, str)
    assert len(first_page) > 0

    # Check that the first page indicates there's more content
    assert 'Content truncated' in first_page

    # Extract the next start_index from the message
    import re

    match = re.search(r'start_index=(\d+)', first_page)
    assert match is not None, 'Could not find next start_index in the result'

    next_start_index = int(match.group(1))
    assert next_start_index > 0, 'Next start_index should be greater than 0'

    # Get the second page
    second_page = await read_documentation(
        ctx, url=url, max_length=small_max_length, start_index=next_start_index
    )

    # Verify the second page
    assert second_page is not None
    assert isinstance(second_page, str)
    assert len(second_page) > 0

    # Check that the content of the two pages is different
    # We'll compare the first 100 characters of each page after the URL line
    first_page_content = first_page.split('\n\n', 1)[1][:100]
    second_page_content = second_page.split('\n\n', 1)[1][:100]

    assert first_page_content != second_page_content, (
        'First and second page content should be different'
    )

    print('\nPagination test successful:')
    print(f'First page start: {first_page_content}')
    print(f'Second page start: {second_page_content}')
