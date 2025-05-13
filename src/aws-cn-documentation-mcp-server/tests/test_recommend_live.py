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
"""Live test for the recommend tool in the AWS Documentation MCP server."""

import asyncio
import pytest
from awslabs.aws_cn_documentation_mcp_server.server import recommend


class MockContext:
    """Mock context for testing."""

    async def error(self, message):
        """Mock error method."""
        print(f'Error: {message}')


@pytest.mark.asyncio
@pytest.mark.live
async def test_recommend_live():
    """Test the recommend tool with a live API call."""
    # Use a real AWS documentation URL
    url = 'https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html'
    ctx = MockContext()

    # Call the recommend function
    results = await recommend(ctx, url=url)

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
