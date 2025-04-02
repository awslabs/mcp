"""Live test for the recommend tool in the AWS Documentation MCP server."""

import asyncio
import pytest
from awslabs.aws_documentation_mcp_server.server import RecommendParams, recommend


@pytest.mark.asyncio
@pytest.mark.live
async def test_recommend_live():
    """Test the recommend tool with a live API call."""
    # Use a real AWS documentation URL
    url = 'https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html'
    params = RecommendParams(url=url)

    # Call the recommend function
    results = await recommend(params)

    # Verify the results
    assert results is not None
    assert len(results) > 0

    # Check that each result has the expected structure
    for result in results:
        assert result.url is not None and result.url != ''
        assert result.title is not None and result.title != ''
        # Context is optional, so we don't assert on it

    # Print results for debugging (will show in pytest output with -v flag)
    print(f'\nReceived {len(results)} recommendations:')
    for i, result in enumerate(results, 1):
        print(f'\n--- Recommendation {i} ---')
        print(f'Title: {result.title}')
        print(f'URL: {result.url}')
        if result.context:
            print(f'Context: {result.context}')


if __name__ == '__main__':
    # This allows running the test directly for debugging
    asyncio.run(test_recommend_live())
