"""Live test for the search_documentation tool in the AWS Documentation MCP server."""

import asyncio
import pytest
from awslabs.aws_documentation_mcp_server.server import (
    SearchDocumentationParams,
    search_documentation,
)


@pytest.mark.asyncio
@pytest.mark.live
async def test_search_documentation_live():
    """Test the search_documentation tool with a live API call."""
    # Use a search phrase that should return results
    search_phrase = 'S3 bucket naming rules'
    params = SearchDocumentationParams(search_phrase=search_phrase, limit=5)

    # Call the search_documentation function
    results = await search_documentation(params)

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
    params = SearchDocumentationParams(search_phrase=search_phrase, limit=5)

    # Call the search_documentation function
    results = await search_documentation(params)

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

    # Test with limit=3
    params_small = SearchDocumentationParams(search_phrase=search_phrase, limit=3)
    results_small = await search_documentation(params_small)

    # Test with limit=10
    params_large = SearchDocumentationParams(search_phrase=search_phrase, limit=10)
    results_large = await search_documentation(params_large)

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
