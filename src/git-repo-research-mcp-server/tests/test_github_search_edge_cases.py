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
"""Tests for GitHub search functionality edge cases and error handling."""

import pytest
import requests
from awslabs.git_repo_research_mcp_server.github_search import (
    clean_github_url,
    extract_org_from_url,
    github_graphql_request,
    github_repo_search_graphql,
    github_repo_search_rest,
    github_repo_search_wrapper,
)
from unittest.mock import MagicMock, patch


def test_clean_github_url_basic():
    """Test basic URL cleaning."""
    input_url = 'https://github.com/aws-samples/aws-cdk-examples/blob/main/index.ts'
    expected = 'https://github.com/aws-samples/aws-cdk-examples'
    assert clean_github_url(input_url) == expected


def test_extract_org_from_url_basic():
    """Test basic organization extraction."""
    input_url = 'https://github.com/aws-samples/repo'
    expected = 'aws-samples'
    assert extract_org_from_url(input_url) == expected


@pytest.mark.asyncio
async def test_graphql_request_rate_limit():
    """Test GraphQL rate limit handling."""
    import time as time_module  # Renamed to avoid conflict

    current_time = int(time_module.time())

    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = 'API rate limit exceeded'
        mock_response.headers = {'X-RateLimit-Reset': str(current_time + 30)}
        mock_post.return_value = mock_response

        result = github_graphql_request(query='query{}', variables={}, token=None)

        assert result == {'data': {'search': {'edges': []}}}


def test_github_graphql_request_rate_limit_no_token():
    """Test GitHub GraphQL request function with rate limiting and no token."""
    with patch('requests.post') as mock_post:
        # Configure the mock for rate limit response with no token
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 403
        rate_limit_response.text = 'API rate limit exceeded'
        mock_post.return_value = rate_limit_response

        # Call the function without a token
        result = github_graphql_request(
            query='test query', variables={'query': 'test', 'numResults': 2}, token=None
        )

        # Verify the result - should return empty response without waiting
        assert result == {'data': {'search': {'edges': []}}}

        # Verify post was called once
        mock_post.assert_called_once()


def test_github_graphql_request_http_error():
    """Test GitHub GraphQL request function with HTTP error."""
    with patch('requests.post') as mock_post:
        # Configure the mock to raise an HTTP error
        mock_post.side_effect = requests.exceptions.HTTPError('404 Client Error')

        # Call the function and expect it to raise the exception after retries
        with pytest.raises(requests.exceptions.HTTPError):
            github_graphql_request(
                query='test query',
                variables={'query': 'test', 'numResults': 2},
                token='test_token',
            )


def test_github_graphql_request_auth_failure():
    """Test GitHub GraphQL request function with authentication failure."""
    with patch('requests.post') as mock_post:
        # Configure the mock for auth failure response
        auth_failure = MagicMock()
        auth_failure.status_code = 401
        auth_failure.raise_for_status.side_effect = requests.exceptions.HTTPError(
            '401 Client Error: Unauthorized'
        )
        auth_failure.response = auth_failure
        mock_post.side_effect = requests.exceptions.HTTPError(
            '401 Client Error: Unauthorized', response=auth_failure
        )

        # Call the function and expect it to raise the exception without retries
        with pytest.raises(requests.exceptions.HTTPError):
            github_graphql_request(
                query='test query',
                variables={'query': 'test', 'numResults': 2},
                token='invalid_token',
            )

        # Verify post was called only once (no retries)
        mock_post.assert_called_once()


def test_github_graphql_request_connection_error():
    """Test GitHub GraphQL request function with connection error."""
    with patch('requests.post') as mock_post:
        # Configure the mock to raise a connection error
        mock_post.side_effect = requests.exceptions.ConnectionError('Connection refused')

        # Call the function and expect it to raise the exception after retries
        with pytest.raises(requests.exceptions.ConnectionError):
            github_graphql_request(
                query='test query',
                variables={'query': 'test', 'numResults': 2},
                token='test_token',
            )


def test_github_repo_search_graphql_with_errors():
    """Test GitHub repository search with GraphQL API errors."""
    with patch(
        'awslabs.git_repo_research_mcp_server.github_search.github_graphql_request'
    ) as mock_request:
        # Configure the mock to return an error response
        mock_request.return_value = {
            'errors': [{'message': 'Something went wrong'}, {'message': 'Another error occurred'}]
        }

        # Call the function
        results = github_repo_search_graphql(
            keywords=['mcp', 'aws'],
            organizations=['awslabs', 'aws-samples'],
            num_results=2,
            token='test_token',
        )

        # Verify the results - should be empty due to errors
        assert results == []


@pytest.mark.github
def test_github_repo_search_graphql_with_exception():
    """Test GitHub repository search with GraphQL API exception."""
    # Skip in CI environment
    # if os.environ.get('CI') == 'true':
    #     pytest.skip('Skipping GitHub API test in CI environment')

    with patch(
        'awslabs.git_repo_research_mcp_server.github_search.github_graphql_request'
    ) as mock_request:
        # Configure the mock to raise an exception
        mock_request.side_effect = Exception('Test exception')

        # Call the function
        results = github_repo_search_graphql(
            keywords=['mcp', 'aws'],
            organizations=['awslabs', 'aws-samples'],
            num_results=2,
            token='test_token',
        )

        # Verify the results - should be empty due to exception
        assert results == []


@pytest.mark.github
def test_github_repo_search_graphql_duplicate_urls():
    """Test GitHub repository search with duplicate URLs in results."""
    # Skip in CI environment
    # if os.environ.get('CI') == 'true':
    #     pytest.skip('Skipping GitHub API test in CI environment')

    with patch(
        'awslabs.git_repo_research_mcp_server.github_search.github_graphql_request'
    ) as mock_request:
        # Configure the mock to return duplicate URLs
        mock_request.return_value = {
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
                                'description': 'Model Context Protocol',
                                'stargazerCount': 100,
                                'updatedAt': '2023-01-01T00:00:00Z',
                                'primaryLanguage': {'name': 'Python'},
                                'repositoryTopics': {
                                    'nodes': [
                                        {'topic': {'name': 'llm'}},
                                        {'topic': {'name': 'ai'}},
                                    ]
                                },
                                'licenseInfo': {'name': 'Apache License 2.0'},
                                'forkCount': 20,
                                'openIssues': {'totalCount': 5},
                                'homepageUrl': 'https://awslabs.github.io/mcp/',
                            }
                        },
                        {
                            'node': {
                                'nameWithOwner': 'awslabs/mcp',  # Same repo
                                'name': 'mcp',
                                'owner': {'login': 'awslabs'},
                                'url': 'https://github.com/awslabs/mcp',  # Duplicate URL
                                'description': 'Model Context Protocol',
                                'stargazerCount': 100,
                                'updatedAt': '2023-01-01T00:00:00Z',
                                'primaryLanguage': {'name': 'Python'},
                                'repositoryTopics': {
                                    'nodes': [
                                        {'topic': {'name': 'llm'}},
                                        {'topic': {'name': 'ai'}},
                                    ]
                                },
                                'licenseInfo': {'name': 'Apache License 2.0'},
                                'forkCount': 20,
                                'openIssues': {'totalCount': 5},
                                'homepageUrl': 'https://awslabs.github.io/mcp/',
                            }
                        },
                    ],
                }
            }
        }

        # Call the function
        results = github_repo_search_graphql(
            keywords=['mcp', 'aws'],
            organizations=['awslabs', 'aws-samples'],
            num_results=2,
            token='test_token',
        )

        # Verify the results - should only include one entry despite duplicate URLs
        assert len(results) == 1
        assert results[0]['url'] == 'https://github.com/awslabs/mcp'


@pytest.mark.github
def test_github_repo_search_graphql_org_mismatch():
    """Test GitHub repository search with organization mismatch."""
    # Skip in CI environment
    # if os.environ.get('CI') == 'true':
    #     pytest.skip('Skipping GitHub API test in CI environment')

    with patch(
        'awslabs.git_repo_research_mcp_server.github_search.github_graphql_request'
    ) as mock_request:
        # Configure the mock to return a repo from a different organization
        mock_request.return_value = {
            'data': {
                'search': {
                    'repositoryCount': 1,
                    'edges': [
                        {
                            'node': {
                                'nameWithOwner': 'different-org/repo',
                                'name': 'repo',
                                'owner': {'login': 'different-org'},  # Not in target orgs
                                'url': 'https://github.com/different-org/repo',
                                'description': 'Some repository',
                                'stargazerCount': 50,
                                'updatedAt': '2023-01-01T00:00:00Z',
                                'primaryLanguage': {'name': 'Python'},
                                'repositoryTopics': {'nodes': []},
                                'licenseInfo': {'name': 'MIT License'},
                                'forkCount': 10,
                                'openIssues': {'totalCount': 2},
                                'homepageUrl': None,
                            }
                        },
                    ],
                }
            }
        }

        # Call the function
        results = github_repo_search_graphql(
            keywords=['repo'],
            organizations=['awslabs', 'aws-samples'],  # Target orgs don't include different-org
            num_results=2,
            token='test_token',
        )

        # Verify the results - should be empty due to org mismatch
        assert results == []


@pytest.mark.github
def test_github_repo_search_rest_with_exception():
    """Test GitHub repository search with REST API exception."""
    # Skip in CI environment
    # if os.environ.get('CI') == 'true':
    #     pytest.skip('Skipping GitHub API test in CI environment')

    with patch('requests.get') as mock_get:
        # Configure the mock to raise an exception
        mock_get.side_effect = Exception('Test exception')

        # Call the function
        results = github_repo_search_rest(
            keywords=['mcp', 'aws'],
            organizations=['awslabs', 'aws-samples'],
            num_results=2,
        )

        # Verify the results - should be empty due to exception
        assert results == []


@pytest.mark.github
def test_github_repo_search_rest_with_http_error():
    """Test GitHub repository search with REST API HTTP error."""
    # Skip in CI environment
    # if os.environ.get('CI') == 'true':
    #     pytest.skip('Skipping GitHub API test in CI environment')

    with patch('requests.get') as mock_get:
        # Configure the mock to raise an HTTP error
        mock_get.side_effect = requests.exceptions.HTTPError('404 Client Error')

        # Call the function
        results = github_repo_search_rest(
            keywords=['mcp', 'aws'],
            organizations=['awslabs', 'aws-samples'],
            num_results=2,
        )

        # Verify the results - should be empty due to HTTP error
        assert results == []


@pytest.mark.github
def test_github_repo_search_rest_with_duplicate_urls():
    """Test GitHub repository search with REST API and duplicate URLs."""
    # Skip in CI environment
    # if os.environ.get('CI') == 'true':
    #     pytest.skip('Skipping GitHub API test in CI environment')

    with patch('requests.get') as mock_get:
        # Configure the mock to return duplicate URLs across different orgs
        mock_response1 = MagicMock()
        mock_response1.json.return_value = {
            'items': [
                {
                    'full_name': 'awslabs/mcp',
                    'html_url': 'https://github.com/awslabs/mcp',
                    'description': 'Model Context Protocol',
                    'stargazers_count': 100,
                    'updated_at': '2023-01-01T00:00:00Z',
                    'language': 'Python',
                    'topics': ['llm', 'ai'],
                    'license': {'name': 'Apache License 2.0'},
                    'forks_count': 20,
                    'open_issues_count': 5,
                    'homepage': 'https://awslabs.github.io/mcp/',
                }
            ]
        }
        mock_response1.status_code = 200

        mock_response2 = MagicMock()
        mock_response2.json.return_value = {
            'items': [
                {
                    'full_name': 'awslabs/mcp',  # Same repo from different org search
                    'html_url': 'https://github.com/awslabs/mcp',  # Duplicate URL
                    'description': 'Model Context Protocol',
                    'stargazers_count': 100,
                    'updated_at': '2023-01-01T00:00:00Z',
                    'language': 'Python',
                    'topics': ['llm', 'ai'],
                    'license': {'name': 'Apache License 2.0'},
                    'forks_count': 20,
                    'open_issues_count': 5,
                    'homepage': 'https://awslabs.github.io/mcp/',
                }
            ]
        }
        mock_response2.status_code = 200

        # Return different responses for different organizations
        mock_get.side_effect = [mock_response1, mock_response2]

        # Call the function
        results = github_repo_search_rest(
            keywords=['mcp', 'aws'],
            organizations=['awslabs', 'aws-samples'],
            num_results=2,
        )

        # Verify the results - should only include one entry despite duplicate URLs
        assert len(results) == 1
        assert results[0]['url'] == 'https://github.com/awslabs/mcp'


@pytest.mark.github
def test_github_repo_search_rest_with_license_filter():
    """Test GitHub repository search with REST API and license filter."""
    # Skip in CI environment
    # if os.environ.get('CI') == 'true':
    #     pytest.skip('Skipping GitHub API test in CI environment')

    with patch('requests.get') as mock_get:
        # Configure the mock to return repos with different licenses
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'items': [
                {
                    'full_name': 'awslabs/mcp',
                    'html_url': 'https://github.com/awslabs/mcp',
                    'description': 'Model Context Protocol',
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
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Call the function with license filter
        results = github_repo_search_rest(
            keywords=['aws'],
            organizations=['awslabs'],
            num_results=2,
            license_filter=['Apache License 2.0'],  # Only include Apache License 2.0
        )

        # Verify the results - should only include the Apache License 2.0 repository
        assert len(results) == 1
        assert results[0]['url'] == 'https://github.com/awslabs/mcp'
        assert results[0]['license'] == 'Apache License 2.0'


@pytest.mark.github
def test_github_repo_search_wrapper_with_string_keywords():
    """Test GitHub repository search wrapper with string keywords."""
    # Skip in CI environment
    # if os.environ.get('CI') == 'true':
    #     pytest.skip('Skipping GitHub API test in CI environment')

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
            }
        ]

        # Call the function with a string keyword
        results = github_repo_search_wrapper(keywords='mcp aws')

        # Verify the mock was called correctly
        mock_rest.assert_called_once_with(
            keywords=['mcp', 'aws'],  # String should be split into list
            organizations=['aws-samples', 'aws-solutions-library-samples', 'awslabs'],
            num_results=5,
            license_filter=None,
        )

        # Verify the results
        assert len(results) == 1
        assert results[0]['url'] == 'https://github.com/awslabs/mcp'


@pytest.mark.github
def test_github_repo_search_wrapper_with_args():
    """Test GitHub repository search wrapper with args parameter."""
    # Skip in CI environment
    # if os.environ.get('CI') == 'true':
    #     pytest.skip('Skipping GitHub API test in CI environment')

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
            }
        ]

        # Call the function with args parameter
        results = github_repo_search_wrapper(args=['mcp', 'aws'])

        # Verify the mock was called correctly
        mock_rest.assert_called_once_with(
            keywords=['mcp', 'aws'],
            organizations=['aws-samples', 'aws-solutions-library-samples', 'awslabs'],
            num_results=5,
            license_filter=None,
        )

        # Verify the results
        assert len(results) == 1
        assert results[0]['url'] == 'https://github.com/awslabs/mcp'


@pytest.mark.github
def test_github_repo_search_wrapper_with_generic_kwargs():
    """Test GitHub repository search wrapper with generic kwargs."""
    # Skip in CI environment
    # if os.environ.get('CI') == 'true':
    #     pytest.skip('Skipping GitHub API test in CI environment')

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
            }
        ]

        # Call the function with generic kwargs
        results = github_repo_search_wrapper(query='mcp aws', other_param='value')

        # Verify the mock was called correctly - should extract keywords from all values
        mock_rest.assert_called_once()
        call_args = mock_rest.call_args[1]
        assert 'mcp' in call_args['keywords']
        assert 'aws' in call_args['keywords']
        assert 'value' in call_args['keywords']

        # Verify the results
        assert len(results) == 1
        assert results[0]['url'] == 'https://github.com/awslabs/mcp'


@pytest.mark.github
def test_github_repo_search_wrapper_exception():
    """Test GitHub repository search wrapper with exception."""
    # Skip in CI environment
    # if os.environ.get('CI') == 'true':
    #     pytest.skip('Skipping GitHub API test in CI environment')

    with (
        patch('os.environ.get') as mock_env,
        patch(
            'awslabs.git_repo_research_mcp_server.github_search.github_repo_search_rest'
        ) as mock_rest,
    ):
        # Configure the mocks
        mock_env.return_value = None  # No token
        mock_rest.side_effect = Exception('Test exception')

        # Call the function
        results = github_repo_search_wrapper(keywords=['mcp', 'aws'])

        # Verify the results - should be empty due to exception
        assert results == []
