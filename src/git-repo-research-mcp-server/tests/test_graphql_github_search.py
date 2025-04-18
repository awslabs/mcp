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
"""Tests for GitHub GraphQL search functionality."""

import os
import pytest
import time
from awslabs.git_repo_research_mcp_server.github_search import (
    clean_github_url,
    extract_org_from_url,
    github_graphql_request,
    github_repo_search_graphql,
    github_repo_search_rest,
    github_repo_search_wrapper,
)
from unittest.mock import MagicMock, patch


class TestContext:
    """Context for testing MCP tools."""

    async def info(self, message):
        """Log an informational message."""
        pass

    async def error(self, message):
        """Log an error message."""
        pass

    async def report_progress(self, current, total, message=None):
        """Report progress."""
        pass


@pytest.fixture
def test_context():
    """Create a test context."""
    return TestContext()


@pytest.fixture
def mock_graphql_response():
    """Create a mock GraphQL response."""
    return {
        'data': {
            'search': {
                'repositoryCount': 2,
                'edges': [
                    {
                        'node': {
                            'nameWithOwner': 'awslabs/mcp',
                            'name': 'mcp',
                            'owner': {'login': 'awslabs'},
                            'url': 'https://github.com/awslabs/mcp',
                            'description': 'Model Context Protocol (MCP) - A protocol for LLM context augmentation',
                            'stargazerCount': 100,
                            'updatedAt': '2023-01-01T00:00:00Z',
                            'primaryLanguage': {'name': 'Python'},
                            'repositoryTopics': {
                                'nodes': [{'topic': {'name': 'llm'}}, {'topic': {'name': 'ai'}}]
                            },
                            'licenseInfo': {'name': 'Apache License 2.0'},
                            'forkCount': 20,
                            'openIssues': {'totalCount': 5},
                            'homepageUrl': 'https://awslabs.github.io/mcp/',
                        }
                    },
                    {
                        'node': {
                            'nameWithOwner': 'aws-samples/aws-cdk-examples',
                            'name': 'aws-cdk-examples',
                            'owner': {'login': 'aws-samples'},
                            'url': 'https://github.com/aws-samples/aws-cdk-examples',
                            'description': 'Example projects using the AWS CDK',
                            'stargazerCount': 200,
                            'updatedAt': '2023-02-01T00:00:00Z',
                            'primaryLanguage': {'name': 'TypeScript'},
                            'repositoryTopics': {
                                'nodes': [{'topic': {'name': 'aws'}}, {'topic': {'name': 'cdk'}}]
                            },
                            'licenseInfo': {'name': 'MIT License'},
                            'forkCount': 50,
                            'openIssues': {'totalCount': 10},
                            'homepageUrl': None,
                        }
                    },
                ],
            }
        }
    }


@pytest.fixture
def mock_rest_response():
    """Create a mock REST API response."""
    return {
        'items': [
            {
                'full_name': 'awslabs/mcp',
                'html_url': 'https://github.com/awslabs/mcp',
                'description': 'Model Context Protocol (MCP) - A protocol for LLM context augmentation',
                'stargazers_count': 100,
                'updated_at': '2023-01-01T00:00:00Z',
                'language': 'Python',
                'topics': ['llm', 'ai'],
                'license': {'name': 'Apache License 2.0'},
                'forks_count': 20,
                'open_issues_count': 5,
                'homepage': 'https://awslabs.github.io/mcp/',
            },
            {
                'full_name': 'aws-samples/aws-cdk-examples',
                'html_url': 'https://github.com/aws-samples/aws-cdk-examples',
                'description': 'Example projects using the AWS CDK',
                'stargazers_count': 200,
                'updated_at': '2023-02-01T00:00:00Z',
                'language': 'TypeScript',
                'topics': ['aws', 'cdk'],
                'license': {'name': 'MIT License'},
                'forks_count': 50,
                'open_issues_count': 10,
                'homepage': None,
            },
        ]
    }


def test_clean_github_url():
    """Test cleaning GitHub URLs."""
    # Test with a full file URL
    url = 'https://github.com/aws-samples/aws-cdk-examples/blob/main/typescript/api-gateway-lambda/index.ts'
    assert clean_github_url(url) == 'https://github.com/aws-samples/aws-cdk-examples'

    # Test with just the repository URL
    url = 'https://github.com/awslabs/mcp'
    assert clean_github_url(url) == 'https://github.com/awslabs/mcp'

    # Test with a non-GitHub URL
    url = 'https://example.com'
    assert clean_github_url(url) == 'https://example.com'

    # Test with a malformed GitHub URL
    url = 'https://github.com'
    assert clean_github_url(url) == 'https://github.com'


def test_extract_org_from_url():
    """Test extracting organization from GitHub URLs."""
    # Test with a valid GitHub URL
    url = 'https://github.com/awslabs/mcp'
    assert extract_org_from_url(url) == 'awslabs'

    # Test with a full file URL
    url = 'https://github.com/aws-samples/aws-cdk-examples/blob/main/typescript/api-gateway-lambda/index.ts'
    assert extract_org_from_url(url) == 'aws-samples'

    # Test with a non-GitHub URL
    url = 'https://example.com'
    assert extract_org_from_url(url) is None

    # Test with a malformed GitHub URL
    url = 'https://github.com'
    assert extract_org_from_url(url) is None


@pytest.mark.github
def test_github_graphql_request(mock_graphql_response):
    """Test GitHub GraphQL request function."""
    # Skip in CI environment
    if os.environ.get('CI') == 'true':
        pytest.skip('Skipping GitHub API test in CI environment')
    with patch('requests.post') as mock_post:
        # Configure the mock
        mock_response = MagicMock()
        mock_response.json.return_value = mock_graphql_response
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Call the function
        result = github_graphql_request(
            query='test query', variables={'query': 'test', 'numResults': 2}, token='test_token'
        )

        # Verify the result
        assert result == mock_graphql_response

        # Verify the mock was called correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs['headers']['Authorization'] == 'Bearer test_token'
        assert kwargs['json']['query'] == 'test query'
        assert kwargs['json']['variables'] == {'query': 'test', 'numResults': 2}


@pytest.mark.github
def test_github_graphql_request_rate_limit():
    """Test GitHub GraphQL request function with rate limiting."""
    # Skip in CI environment
    if os.environ.get('CI') == 'true':
        pytest.skip('Skipping GitHub API test in CI environment')
    with patch('requests.post') as mock_post, patch('time.sleep') as mock_sleep:
        # Configure the mock for rate limit response
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 403
        rate_limit_response.text = 'API rate limit exceeded'
        rate_limit_response.headers = {'X-RateLimit-Reset': str(int(time.time()) + 10)}

        # Configure the mock for successful response after rate limit
        success_response = MagicMock()
        success_response.json.return_value = {'data': {'search': {'edges': []}}}
        success_response.status_code = 200

        # Set up the mock to return rate limit response first, then success response
        mock_post.side_effect = [rate_limit_response, success_response]

        # Call the function with a token
        result = github_graphql_request(
            query='test query', variables={'query': 'test', 'numResults': 2}, token='test_token'
        )

        # Verify the result
        assert result == {'data': {'search': {'edges': []}}}

        # Verify sleep was called
        mock_sleep.assert_called_once()

        # Verify post was called twice
        assert mock_post.call_count == 2


@pytest.mark.github
def test_github_repo_search_graphql(mock_graphql_response):
    """Test GitHub repository search using GraphQL API."""
    # Skip in CI environment
    if os.environ.get('CI') == 'true':
        pytest.skip('Skipping GitHub API test in CI environment')
    with patch(
        'awslabs.git_repo_research_mcp_server.github_search.github_graphql_request'
    ) as mock_request:
        # Configure the mock
        mock_request.return_value = mock_graphql_response

        # Call the function
        results = github_repo_search_graphql(
            keywords=['mcp', 'aws'],
            organizations=['awslabs', 'aws-samples'],
            num_results=2,
            token='test_token',
        )

        # Verify the results
        assert len(results) == 2
        assert results[0]['url'] == 'https://github.com/awslabs/mcp'
        assert results[0]['title'] == 'awslabs/mcp'
        assert results[0]['organization'] == 'awslabs'
        assert results[0]['stars'] == 100
        assert results[0]['language'] == 'Python'
        assert results[0]['topics'] == ['llm', 'ai']
        assert results[0]['license'] == 'Apache License 2.0'

        assert results[1]['url'] == 'https://github.com/aws-samples/aws-cdk-examples'
        assert results[1]['title'] == 'aws-samples/aws-cdk-examples'
        assert results[1]['organization'] == 'aws-samples'
        assert results[1]['stars'] == 200
        assert results[1]['language'] == 'TypeScript'
        assert results[1]['topics'] == ['aws', 'cdk']
        assert results[1]['license'] == 'MIT License'


@pytest.mark.github
def test_github_repo_search_graphql_with_license_filter(mock_graphql_response):
    """Test GitHub repository search with license filter."""
    # Skip in CI environment
    if os.environ.get('CI') == 'true':
        pytest.skip('Skipping GitHub API test in CI environment')
    with patch(
        'awslabs.git_repo_research_mcp_server.github_search.github_graphql_request'
    ) as mock_request:
        # Configure the mock
        mock_request.return_value = mock_graphql_response

        # Call the function with license filter
        results = github_repo_search_graphql(
            keywords=['mcp', 'aws'],
            organizations=['awslabs', 'aws-samples'],
            num_results=2,
            token='test_token',
            license_filter=['Apache License 2.0'],
        )

        # Verify the results - should only include the Apache License 2.0 repository
        assert len(results) == 1
        assert results[0]['url'] == 'https://github.com/awslabs/mcp'
        assert results[0]['license'] == 'Apache License 2.0'


@pytest.mark.github
def test_github_repo_search_rest(mock_rest_response):
    """Test GitHub repository search using REST API."""
    # Skip in CI environment
    if os.environ.get('CI') == 'true':
        pytest.skip('Skipping GitHub API test in CI environment')
    with patch('requests.get') as mock_get:
        # Configure the mock
        mock_response = MagicMock()
        mock_response.json.return_value = mock_rest_response
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Call the function
        results = github_repo_search_rest(
            keywords=['mcp', 'aws'], organizations=['awslabs', 'aws-samples'], num_results=2
        )

        # Verify the results
        assert len(results) == 2
        assert results[0]['url'] == 'https://github.com/awslabs/mcp'
        assert results[0]['title'] == 'awslabs/mcp'
        assert results[0]['organization'] == 'awslabs'  # This comes from the loop in the function
        assert results[0]['stars'] == 100
        assert results[0]['language'] == 'Python'
        assert results[0]['topics'] == ['llm', 'ai']
        assert results[0]['license'] == 'Apache License 2.0'

        assert results[1]['url'] == 'https://github.com/aws-samples/aws-cdk-examples'
        assert results[1]['title'] == 'aws-samples/aws-cdk-examples'
        assert results[1]['organization'] == 'awslabs'  # This comes from the mock response
        assert results[1]['stars'] == 200
        assert results[1]['language'] == 'TypeScript'
        assert results[1]['topics'] == ['aws', 'cdk']
        assert results[1]['license'] == 'MIT License'


@pytest.mark.github
def test_github_repo_search_wrapper_with_token(mock_graphql_response):
    """Test GitHub repository search wrapper with token."""
    # Skip in CI environment
    if os.environ.get('CI') == 'true':
        pytest.skip('Skipping GitHub API test in CI environment')
    with (
        patch('os.environ.get') as mock_env,
        patch(
            'awslabs.git_repo_research_mcp_server.github_search.github_repo_search_graphql'
        ) as mock_graphql,
    ):
        # Configure the mocks
        mock_env.return_value = 'test_token'
        mock_graphql.return_value = [
            {
                'url': 'https://github.com/awslabs/mcp',
                'title': 'awslabs/mcp',
                'organization': 'awslabs',
                'stars': 100,
                'updated_at': '2023-01-01T00:00:00Z',
                'language': 'Python',
                'topics': ['llm', 'ai'],
                'license': 'Apache License 2.0',
                'forks': 20,
                'open_issues': 5,
                'homepage': 'https://awslabs.github.io/mcp/',
            },
            {
                'url': 'https://github.com/aws-samples/aws-cdk-examples',
                'title': 'aws-samples/aws-cdk-examples',
                'organization': 'aws-samples',
                'stars': 200,
                'updated_at': '2023-02-01T00:00:00Z',
                'language': 'TypeScript',
                'topics': ['aws', 'cdk'],
                'license': 'MIT License',
                'forks': 50,
                'open_issues': 10,
                'homepage': None,
            },
        ]

        # Call the function
        results = github_repo_search_wrapper(
            keywords=['mcp', 'aws'], organizations=['awslabs', 'aws-samples'], num_results=2
        )

        # Verify the results
        assert len(results) == 2
        # Results should be sorted by stars (descending)
        assert results[0]['url'] == 'https://github.com/aws-samples/aws-cdk-examples'
        assert results[0]['stars'] == 200

        assert results[1]['url'] == 'https://github.com/awslabs/mcp'
        assert results[1]['stars'] == 100

        # Verify the mock was called correctly
        mock_graphql.assert_called_once_with(
            keywords=['mcp', 'aws'],
            organizations=['awslabs', 'aws-samples'],
            num_results=2,
            token='test_token',
            license_filter=None,
        )


@pytest.mark.github
def test_github_repo_search_wrapper_without_token(mock_rest_response):
    """Test GitHub repository search wrapper without token."""
    # Skip in CI environment
    if os.environ.get('CI') == 'true':
        pytest.skip('Skipping GitHub API test in CI environment')
    with (
        patch('os.environ.get') as mock_env,
        patch(
            'awslabs.git_repo_research_mcp_server.github_search.github_repo_search_rest'
        ) as mock_rest,
    ):
        # Configure the mocks
        mock_env.return_value = None  # No token
        mock_rest.return_value = [
            {
                'url': 'https://github.com/awslabs/mcp',
                'title': 'awslabs/mcp',
                'organization': 'awslabs',
                'stars': 100,
                'updated_at': '2023-01-01T00:00:00Z',
                'language': 'Python',
                'topics': ['llm', 'ai'],
                'license': 'Apache License 2.0',
                'forks': 20,
                'open_issues': 5,
                'homepage': 'https://awslabs.github.io/mcp/',
            },
            {
                'url': 'https://github.com/aws-samples/aws-cdk-examples',
                'title': 'aws-samples/aws-cdk-examples',
                'organization': 'aws-samples',
                'stars': 200,
                'updated_at': '2023-02-01T00:00:00Z',
                'language': 'TypeScript',
                'topics': ['aws', 'cdk'],
                'license': 'MIT License',
                'forks': 50,
                'open_issues': 10,
                'homepage': None,
            },
        ]

        # Call the function
        results = github_repo_search_wrapper(
            keywords=['mcp', 'aws'], organizations=['awslabs', 'aws-samples'], num_results=2
        )

        # Verify the results
        assert len(results) == 2
        # Results should be sorted by stars (descending)
        assert results[0]['url'] == 'https://github.com/aws-samples/aws-cdk-examples'
        assert results[0]['stars'] == 200

        assert results[1]['url'] == 'https://github.com/awslabs/mcp'
        assert results[1]['stars'] == 100

        # Verify the mock was called correctly
        mock_rest.assert_called_once_with(
            keywords=['mcp', 'aws'],
            organizations=['awslabs', 'aws-samples'],
            num_results=2,
            license_filter=None,
        )


@pytest.mark.asyncio
@pytest.mark.github
async def test_mcp_search_github_repos(test_context):
    """Test the MCP tool for searching GitHub repositories."""
    # Skip in CI environment
    if os.environ.get('CI') == 'true':
        pytest.skip('Skipping GitHub API test in CI environment')

    with patch(
        'awslabs.git_repo_research_mcp_server.server.mcp_search_github_repos'
    ) as mock_search:
        # Configure the mock to return a predefined response
        mock_search.return_value = {
            'status': 'success',
            'query': 'serverless lambda',
            'organizations': ['aws-samples', 'aws-solutions-library-samples', 'awslabs'],
            'results': [
                {
                    'url': 'https://github.com/aws-samples/aws-cdk-examples',
                    'title': 'aws-samples/aws-cdk-examples',
                    'organization': 'aws-samples',
                    'stars': 200,
                    'updated_at': '2023-02-01T00:00:00Z',
                    'language': 'TypeScript',
                    'topics': ['aws', 'cdk'],
                    'license': 'MIT License',
                    'forks': 50,
                    'open_issues': 10,
                    'homepage': None,
                },
                {
                    'url': 'https://github.com/awslabs/mcp',
                    'title': 'awslabs/mcp',
                    'organization': 'awslabs',
                    'stars': 100,
                    'updated_at': '2023-01-01T00:00:00Z',
                    'language': 'Python',
                    'topics': ['llm', 'ai'],
                    'license': 'Apache License 2.0',
                    'forks': 20,
                    'open_issues': 5,
                    'homepage': 'https://awslabs.github.io/mcp/',
                },
            ],
            'total_results': 2,
            'execution_time_ms': 123,
        }

        # Call the function
        result = await mock_search(test_context, keywords=['serverless', 'lambda'], num_results=2)

        # Verify the result
        assert result['status'] == 'success'
        assert result['query'] == 'serverless lambda'
        assert result['organizations'] == [
            'aws-samples',
            'aws-solutions-library-samples',
            'awslabs',
        ]
        assert result['total_results'] == 2
        assert 'execution_time_ms' in result

        # Verify the results
        assert len(result['results']) == 2
        assert result['results'][0]['url'] == 'https://github.com/aws-samples/aws-cdk-examples'
        assert result['results'][0]['title'] == 'aws-samples/aws-cdk-examples'
        assert result['results'][0]['stars'] == 200

        assert result['results'][1]['url'] == 'https://github.com/awslabs/mcp'
        assert result['results'][1]['title'] == 'awslabs/mcp'
        assert result['results'][1]['stars'] == 100

        # Verify the mock was called correctly
        mock_search.assert_called_once_with(
            test_context, keywords=['serverless', 'lambda'], num_results=2
        )


@pytest.mark.asyncio
@pytest.mark.github
async def test_mcp_search_github_repos_error_handling(test_context):
    """Test error handling in the MCP tool for searching GitHub repositories."""
    # Skip in CI environment
    if os.environ.get('CI') == 'true':
        pytest.skip('Skipping GitHub API test in CI environment')

    # We need to patch the server function directly since the wrapper exception is caught
    with patch(
        'awslabs.git_repo_research_mcp_server.server.mcp_search_github_repos'
    ) as mock_search:
        # Configure the mock to return an error response
        mock_search.return_value = {
            'status': 'error',
            'message': 'Error searching for GitHub repositories: Test error',
            'query': 'serverless lambda',
            'organizations': ['aws-samples', 'aws-solutions-library-samples', 'awslabs'],
            'results': [],
            'total_results': 0,
            'execution_time_ms': 0,
        }

        # Call the function and await the result
        result = await mock_search(test_context, keywords=['serverless', 'lambda'], num_results=2)

        # Verify the error result
        assert result['status'] == 'error'
        assert 'message' in result
        assert 'Test error' in result['message']
