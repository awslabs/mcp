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
"""Live test for the search_documentation tool in the AWS Documentation MCP server."""

import asyncio
import pytest
from awslabs.aws_documentation_mcp_server.server_aws import search_documentation


class MockContext:
    """Mock context for testing."""

    async def error(self, message):
        """Mock error method."""
        print(f'Error: {message}')


@pytest.mark.asyncio
@pytest.mark.live
async def test_search_documentation_live():
    """Test the search_documentation tool with a live API call."""
    # Use a search phrase that should return results
    search_phrase = 'S3 bucket naming rules'
    ctx = MockContext()

    # Call the search_documentation function
    results = await search_documentation(ctx, search_phrase=search_phrase, limit=5)

    # Verify the results
    assert results is not None
    assert len(results) > 0

    # Check that each result has the expected structure
    for result in results:
        assert result.rank_order > 0
        assert result.url is not None and result.url != ''
        assert result.title is not None and result.title != ''
        # Context is optional, so we don't assert on it

    # Print results for debugging (will show in pytest output with -v flag)
    print(f"\nReceived {len(results)} search results for '{search_phrase}':")
    for i, result in enumerate(results, 1):
        print(f'\n--- Result {i} ---')
        print(f'Rank: {result.rank_order}')
        print(f'Title: {result.title}')
        print(f'URL: {result.url}')
        if result.context:
            print(f'Context: {result.context}')


@pytest.mark.asyncio
@pytest.mark.live
async def test_search_documentation_empty_results():
    """Test the search_documentation tool with a search phrase that should return few or no results."""
    # Use a very specific search phrase that might not have many results
    search_phrase = 'xyzabcnonexistentdocumentationterm123456789'
    ctx = MockContext()

    # Call the search_documentation function
    results = await search_documentation(ctx, search_phrase=search_phrase, limit=5)

    # We don't assert on the number of results, as it might change over time
    # Just verify that the function returns a valid response
    assert results is not None

    # Print results for debugging
    print(f"\nReceived {len(results)} search results for '{search_phrase}':")
    for i, result in enumerate(results, 1):
        print(f'\n--- Result {i} ---')
        print(f'Rank: {result.rank_order}')
        print(f'Title: {result.title}')
        print(f'URL: {result.url}')
        if result.context:
            print(f'Context: {result.context}')


@pytest.mark.asyncio
@pytest.mark.live
async def test_search_documentation_limit():
    """Test the search_documentation tool with different limit values."""
    search_phrase = 'AWS Lambda'
    ctx = MockContext()

    # Test with limit=3
    results_small = await search_documentation(ctx, search_phrase=search_phrase, limit=3)

    # Test with limit=10
    results_large = await search_documentation(ctx, search_phrase=search_phrase, limit=10)

    # Verify that the limits are respected
    assert len(results_small) <= 3
    assert len(results_large) <= 10

    # If we got at least 3 results for both queries, the small result set should be smaller
    if len(results_small) == 3 and len(results_large) > 3:
        assert len(results_small) < len(results_large)

    print(f'\nReceived {len(results_small)} results with limit=3')
    print(f'Received {len(results_large)} results with limit=10')


if __name__ == '__main__':
    # This allows running the test directly for debugging
    asyncio.run(test_search_documentation_live())
