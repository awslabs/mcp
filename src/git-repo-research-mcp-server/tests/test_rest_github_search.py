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
"""Live test for the GitHub repository search functionality in the Git Repository Research MCP Server."""

import asyncio
import pytest

# Import the server functions
from awslabs.git_repo_research_mcp_server.server import (
    mcp_search_github_repos as search_repositories_on_github,
)


class MockContext:
    """Mock context for testing."""

    def info(self, message):
        """Mock info method."""
        print(f'Info: {message}')

    def error(self, message):
        """Mock error method."""
        print(f'Error: {message}')


@pytest.mark.asyncio
@pytest.mark.github
async def test_github_repository_search_live():
    """Test searching for GitHub repositories with a live GitHub API call."""
    ctx = MockContext()

    # Test searching for "aws lambda serverless"
    # This should return repositories from AWS organizations related to Lambda and serverless
    search_result = await search_repositories_on_github(
        ctx, keywords=['aws', 'lambda', 'serverless'], num_results=5
    )

    # Verify the results
    assert search_result is not None
    assert 'results' in search_result

    # Check if we have results (if API rate limit wasn't hit)
    if len(search_result['results']) > 0:
        # Print the available keys in the first result for debugging
        print(f'Available keys in result: {list(search_result["results"][0].keys())}')

        # Adapt assertions to the actual structure of the API response
        # We'll test for common fields that should be present in GitHub repo info
        for result in search_result['results']:
            # Check essential fields based on actual API response structure
            assert 'url' in result, 'Missing url field'  # Using url instead of html_url
            assert 'title' in result, 'Missing title field'  # Using title instead of name
            assert 'organization' in result, 'Missing organization field'

            # Check organization is one of the expected ones
            org_name = result['organization'].lower()
            assert org_name in ['aws-samples', 'aws-solutions-library-samples', 'awslabs'], (
                f'Repository from unexpected organization: {org_name}'
            )

    print('\nGitHub search results:')
    for idx, result in enumerate(search_result['results'], 1):
        print(f'\nResult {idx}:')
        print(f'Title: {result["title"]}')
        print(f'Organization: {result["organization"]}')
        print(f'URL: {result["url"]}')
        print(f'Stars: {result.get("stars", "N/A")}')
        print(f'Updated At: {result.get("updated_at", "N/A")}')
        print(f'License: {result.get("license", "N/A")}')
        if result.get('description'):
            print(f'Description: {result["description"]}')


@pytest.mark.asyncio
@pytest.mark.github
async def test_github_repository_search_no_results_live():
    """Test searching for GitHub repositories with a query that should return no results."""
    ctx = MockContext()

    # Test with a very specific query that is unlikely to have repositories
    search_result = await search_repositories_on_github(
        ctx, keywords=['unlikely123456789', 'nonexistentrepo987654321'], num_results=5
    )

    # Verify the results
    assert search_result is not None
    assert 'results' in search_result

    # We don't strictly assert that there are no results, as GitHub search can be unpredictable,
    # but we log the count
    print(f'\nNumber of results for unlikely search terms: {len(search_result["results"])}')

    # If there are any results, log them for examination
    if search_result['results']:
        print('\nUnexpected results found:')
        for idx, result in enumerate(search_result['results'], 1):
            print(f'\nResult {idx}:')
            print(f'Title: {result["title"]}')
            print(f'Organization: {result["organization"]}')
            print(f'Description: {result.get("description", "No description")}')


@pytest.mark.asyncio
@pytest.mark.github
async def test_github_repository_search_with_limit_live():
    """Test searching for GitHub repositories with different result limits."""
    ctx = MockContext()

    # Small number of results
    small_result = await search_repositories_on_github(
        ctx, keywords=['aws', 'dynamodb'], num_results=2
    )

    # Larger number of results
    large_result = await search_repositories_on_github(
        ctx, keywords=['aws', 'dynamodb'], num_results=5
    )

    # Verify the responses are valid
    assert small_result is not None
    assert 'results' in small_result

    assert large_result is not None
    assert 'results' in large_result

    # Log the actual result lengths - don't strictly assert limits
    # as the GitHub API might not honor them exactly
    print(f'\nSmall result count: {len(small_result["results"])}')
    print(f'Large result count: {len(large_result["results"])}')

    # If we got at least 2 results for both queries, the small result set should be smaller
    if len(small_result['results']) == 2 and len(large_result['results']) > 2:
        assert len(small_result['results']) < len(large_result['results'])

    print(f'\nReceived {len(small_result["results"])} results with limit=2')
    print(f'Received {len(large_result["results"])} results with limit=5')


@pytest.mark.asyncio
@pytest.mark.github
async def test_github_repository_order_by_stars_live():
    """Test that GitHub repository search results are ordered by stars."""
    ctx = MockContext()

    # Search for popular AWS repositories
    search_result = await search_repositories_on_github(
        ctx, keywords=['aws', 'cdk'], num_results=10
    )

    # Verify the results structure
    assert search_result is not None
    assert 'results' in search_result

    # Only check ordering if we have results and they contain stars
    if len(search_result['results']) >= 2 and 'stars' in search_result['results'][0]:
        star_counts = [r['stars'] for r in search_result['results']]
        assert star_counts == sorted(star_counts, reverse=True), (
            'Results are not ordered by stars in descending order'
        )

        print('\nResults ordered by stars (descending):')
        for idx, result in enumerate(search_result['results'], 1):
            print(f'{idx}. {result["title"]} - {result["stars"]} stars')


if __name__ == '__main__':
    # This allows running the test directly for debugging
    asyncio.run(test_github_repository_search_live())
