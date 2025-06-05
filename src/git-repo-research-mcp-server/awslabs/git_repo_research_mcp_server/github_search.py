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
"""GitHub repository search functionality for Git Repository Research MCP Server.

This module provides functionality for searching GitHub repositories using the GitHub GraphQL API.
"""

import backoff
import os
import requests
import time
from loguru import logger
from typing import Any, Dict, List, Optional


# GitHub GraphQL API query for repository search
GITHUB_GRAPHQL_QUERY = """
query SearchRepositories($query: String!, $numResults: Int!) {
  search(query: $query, type: REPOSITORY, first: $numResults) {
    repositoryCount
    edges {
      node {
        ... on Repository {
          nameWithOwner
          name
          owner {
            login
          }
          url
          description
          stargazerCount
          updatedAt
          primaryLanguage {
            name
          }
          repositoryTopics(first: 10) {
            nodes {
              topic {
                name
              }
            }
          }
          licenseInfo {
            name
          }
          forkCount
          openIssues: issues(states: OPEN) {
            totalCount
          }
          homepageUrl
        }
      }
    }
  }
}
"""


@backoff.on_exception(
    backoff.expo,
    (requests.exceptions.RequestException, requests.exceptions.HTTPError),
    max_tries=5,
    giveup=lambda e: bool(
        (response := getattr(e, 'response', None))
        and getattr(response, 'status_code', None) == 401
    ),  # Don't retry on auth failures
)
def github_graphql_request(
    query: str, variables: Dict[str, Any], token: Optional[str] = None
) -> Dict[str, Any]:
    """Make a request to the GitHub GraphQL API with exponential backoff for rate limiting.

    Args:
        query: The GraphQL query
        variables: Variables for the GraphQL query
        token: Optional GitHub token for authentication

    Returns:
        The JSON response from the API
    """
    headers = {
        'Content-Type': 'application/json',
    }

    # Add authorization header if token is provided
    if token:
        headers['Authorization'] = f'Bearer {token}'

    try:
        response = requests.post(
            'https://api.github.com/graphql',
            headers=headers,
            json={'query': query, 'variables': variables},
            timeout=10,  # Add 10 second timeout to prevent hanging requests
        )

        # Check for rate limiting
        if response.status_code == 403 and 'rate limit' in response.text.lower():
            # For unauthenticated requests, don't wait - just log and return empty response
            if not token:
                logger.warning(
                    'Rate limited by GitHub API and no token provided. Consider adding a GITHUB_TOKEN.'
                )
                return {'data': {'search': {'edges': []}}}

            # For authenticated requests, check reset time but cap at reasonable value
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
            current_time = int(time.time())
            wait_time = min(max(reset_time - current_time, 0), 60)  # Cap at 60 seconds

            if wait_time > 0:
                logger.warning(f'Rate limited by GitHub API. Waiting {wait_time} seconds.')
                time.sleep(wait_time)
                # Retry the request
                return github_graphql_request(query, variables, token)

        # Raise exception for other HTTP errors
        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f'GitHub API request error: {str(e)}')
        raise


def github_repo_search_graphql(
    keywords: List[str],
    organizations: List[str],
    num_results: int = 5,
    token: Optional[str] = None,
    license_filter: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Search GitHub repositories using the GraphQL API.

    Args:
        keywords: List of keywords to search for
        organizations: List of GitHub organizations to scope the search to
        num_results: Number of results to return
        token: Optional GitHub token for authentication
        license_filter: Optional list of license names to filter repositories by

    Returns:
        List of GitHub repositories matching the search criteria
    """
    # Build the search query with organization filters
    org_filters = ' '.join([f'org:{org}' for org in organizations])
    keyword_string = ' OR '.join(keywords)
    query_string = f'{keyword_string} {org_filters}'

    logger.info(f'Searching GitHub with GraphQL query: {query_string}')

    try:
        # Make the GraphQL request
        variables = {
            'query': query_string,
            'numResults': num_results * 2,  # Request more than needed to filter
        }

        response = github_graphql_request(GITHUB_GRAPHQL_QUERY, variables, token)

        if 'errors' in response:
            error_messages = [
                error.get('message', 'Unknown error') for error in response['errors']
            ]
            logger.error(f'GitHub GraphQL API errors: {", ".join(error_messages)}')
            return []

        # Extract repository data from response
        search_data = response.get('data', {}).get('search', {})
        edges = search_data.get('edges', [])

        repo_results = []
        processed_urls = set()  # To avoid duplicates

        for edge in edges:
            node = edge.get('node', {})

            # Extract repository information
            repo_url = node.get('url', '')
            name_with_owner = node.get('nameWithOwner', '')
            description = node.get('description', '')
            owner = node.get('owner', {}).get('login', '')

            # Skip if we've already processed this URL or if it's not from one of our target organizations
            if repo_url in processed_urls or owner.lower() not in [
                org.lower() for org in organizations
            ]:
                continue

            processed_urls.add(repo_url)

            # Extract primary language if available
            primary_language = node.get('primaryLanguage', {})
            language = primary_language.get('name') if primary_language else None

            # Extract topics if available
            topics_data = node.get('repositoryTopics', {}).get('nodes', [])
            topics = [
                topic.get('topic', {}).get('name') for topic in topics_data if topic.get('topic')
            ]

            # Extract license information if available
            license_info = node.get('licenseInfo', {})
            license_name = license_info.get('name') if license_info else None

            # Skip if license filter is specified and this repository's license doesn't match
            if license_filter and license_name and license_name not in license_filter:
                continue

            # Extract open issues count
            open_issues = node.get('openIssues', {}).get('totalCount', 0)

            # Add to results with additional metadata
            repo_results.append(
                {
                    'url': repo_url,
                    'title': name_with_owner,
                    'description': description,
                    'organization': owner,
                    'stars': node.get('stargazerCount', 0),
                    'updated_at': node.get('updatedAt', ''),
                    'language': language,
                    'topics': topics,
                    'license': license_name,
                    'forks': node.get('forkCount', 0),
                    'open_issues': open_issues,
                    'homepage': node.get('homepageUrl'),
                }
            )

            # Stop if we have enough results
            if len(repo_results) >= num_results:
                break

        logger.info(f'Found {len(repo_results)} GitHub repositories via GraphQL API')
        return repo_results

    except Exception as e:
        logger.error(f'GitHub GraphQL search error: {str(e)}')
        return []


def clean_github_url(url: str) -> str:
    """Clean up GitHub URLs to get the main repository URL.

    For example, convert:
    https://github.com/aws-samples/aws-cdk-examples/blob/main/typescript/api-gateway-lambda/index.ts
    to:
    https://github.com/aws-samples/aws-cdk-examples

    Args:
        url: The GitHub URL to clean

    Returns:
        The cleaned GitHub repository URL
    """
    # Basic implementation - can be enhanced for edge cases
    if 'github.com' not in url:
        return url

    parts = url.split('github.com/')
    if len(parts) < 2:
        return url

    repo_path = parts[1]
    # Extract org/repo part (first two segments)
    repo_segments = repo_path.split('/')
    if len(repo_segments) >= 2:
        return f'https://github.com/{repo_segments[0]}/{repo_segments[1]}'

    return url


def extract_org_from_url(url: str) -> Optional[str]:
    """Extract organization name from GitHub URL.

    Args:
        url: The GitHub URL to extract the organization from

    Returns:
        The organization name, or None if not found
    """
    if 'github.com' not in url:
        return None

    parts = url.split('github.com/')
    if len(parts) < 2:
        return None

    repo_path = parts[1]
    org = repo_path.split('/')[0]
    return org


def github_repo_search_rest(
    keywords: List[str],
    organizations: List[str],
    num_results: int = 5,
    license_filter: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Search GitHub repositories using the REST API.

    This is a fallback for when GraphQL API is rate limited and no token is provided.

    Args:
        keywords: List of keywords to search for
        organizations: List of GitHub organizations to scope the search to
        num_results: Number of results to return
        license_filter: Optional list of license names to filter repositories by

    Returns:
        List of GitHub repositories matching the search criteria
    """
    repo_results = []
    processed_urls = set()

    # Process each organization separately
    for org in organizations:
        try:
            # Build the search query for this organization
            keyword_string = '+OR+'.join(keywords)
            query_string = f'{keyword_string}+org:{org}'

            logger.info(f'Searching GitHub REST API for org {org}')

            # Make the REST API request
            response = requests.get(
                f'https://api.github.com/search/repositories?q={query_string}&sort=stars&order=desc&per_page={num_results}',
                headers={'Accept': 'application/vnd.github.v3+json'},
                timeout=10,  # Add 10 second timeout to prevent hanging requests
            )

            # Check for errors
            response.raise_for_status()

            # Parse the response
            data = response.json()
            items = data.get('items', [])

            # Process each repository
            for item in items:
                repo_url = item.get('html_url', '')

                # Skip if we've already processed this URL
                if repo_url in processed_urls:
                    continue

                processed_urls.add(repo_url)

                # Extract license information if available
                license_info = item.get('license')
                license_name = license_info.get('name') if license_info else None

                # Skip if license filter is specified and this repository's license doesn't match
                if license_filter and license_name and license_name not in license_filter:
                    continue

                # Extract topics if available
                topics = item.get('topics', [])

                # Add to results with additional metadata
                repo_results.append(
                    {
                        'url': repo_url,
                        'title': item.get('full_name', ''),
                        'description': item.get('description', ''),
                        'organization': org,
                        'stars': item.get('stargazers_count', 0),
                        'updated_at': item.get('updated_at', ''),
                        'language': item.get('language'),
                        'topics': topics,
                        'license': license_name,
                        'forks': item.get('forks_count', 0),
                        'open_issues': item.get('open_issues_count', 0),
                        'homepage': item.get('homepage'),
                    }
                )

                # Stop if we have enough results
                if len(repo_results) >= num_results:
                    break

            # Add a small delay between requests to avoid rate limiting
            time.sleep(1)

        except Exception as e:
            logger.error(f'GitHub REST API error for org {org}: {str(e)}')
            continue

    logger.info(f'Found {len(repo_results)} GitHub repositories via REST API')
    return repo_results


def github_repo_search_wrapper(**kwargs) -> List[Dict[str, Any]]:
    """Wrapper for GitHub API search that returns GitHub repository results.

    Args:
        **kwargs: Keyword arguments including:
            - keywords: List of keywords to search for
            - organizations: List of GitHub organizations to scope the search to
            - num_results: Number of results to return

    Returns:
        List of GitHub repositories matching the search criteria
    """
    # Extract keywords from kwargs
    if 'args' in kwargs:
        keywords = kwargs['args']
    elif 'keywords' in kwargs:
        keywords = kwargs['keywords']
    else:
        # Convert all values to strings and split by spaces
        keywords_str = ' '.join(str(value) for value in kwargs.values())
        keywords = keywords_str.split()

    # Ensure keywords is a list
    if isinstance(keywords, str):
        keywords = keywords.split()

    # Get organizations to search in
    organizations = kwargs.get(
        'organizations', ['aws-samples', 'aws-solutions-library-samples', 'awslabs']
    )
    num_results = kwargs.get('num_results', 5)
    license_filter = kwargs.get('license_filter')

    # Get GitHub token from environment variable
    token = os.environ.get('GITHUB_TOKEN')

    try:
        # GraphQL API requires authentication, so only use it if token is provided
        if token:
            logger.info('Using authenticated GitHub GraphQL API')
            results = github_repo_search_graphql(
                keywords=keywords,
                organizations=organizations,
                num_results=num_results,
                token=token,
                license_filter=license_filter,
            )
        # Always use REST API for unauthenticated requests
        else:
            logger.info('Using unauthenticated GitHub REST API (GraphQL requires auth)')
            results = github_repo_search_rest(
                keywords=keywords,
                organizations=organizations,
                num_results=num_results,
                license_filter=license_filter,
            )

        # Sort results by stars (descending) and then by updated_at date
        results.sort(
            key=lambda x: (
                -(x.get('stars', 0) or 0),  # Sort by stars descending
                x.get('updated_at', ''),  # Then by updated_at
            )
        )

        return results
    except Exception as e:
        logger.error(f'GitHub repository search error: {str(e)}')
        return []
