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

"""Tools for the AWS Amplify Gen2 MCP Server."""

import base64
import json
import logging
import os
from datetime import datetime, timedelta
from .consts import (
    DEFAULT_SEARCH_LIMIT,
    DOCUMENTATION_REPO,
    GITHUB_API_BASE,
    PROJECT_TEMPLATE_FILES,
    SAMPLE_REPOSITORIES,
)
from typing import Any, Dict, List, Optional


def search_amplify_documentation(query: str, limit: int = DEFAULT_SEARCH_LIMIT) -> List[Dict]:
    """Search Amplify documentation by browsing the repository structure.

    Args:
        query: Search query string
        limit: Maximum number of results to return

    Returns:
        List of search results with file information and relevance
    """
    try:
        # Since GitHub Code Search API requires auth, we'll use a different approach
        # Get the repository tree and search through file paths and names
        search_results = []

        # Get the repository tree
        tree_url = f"{GITHUB_API_BASE}/repos/{DOCUMENTATION_REPO}/git/trees/main?recursive=1"

        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'AmplifyGen2MCPServer/1.0'
        }

        response = requests.get(tree_url, headers=headers, timeout=10)

        if response.status_code == 200:
            tree_data = response.json()

            # Filter for markdown files and calculate relevance
            for item in tree_data.get('tree', []):
                if item['type'] == 'blob' and item['path'].endswith(('.md', '.mdx')):
                    # Calculate relevance score based on path and filename
                    relevance_score = calculate_relevance_score_from_path(item['path'], query)

                    if relevance_score > 0:  # Only include relevant results
                        search_results.append({
                            'rank_order': len(search_results) + 1,
                            'url': f"https://github.com/{DOCUMENTATION_REPO}/blob/main/{item['path']}",
                            'raw_url': f"https://raw.githubusercontent.com/{DOCUMENTATION_REPO}/main/{item['path']}",
                            'title': extract_title_from_path(item['path']),
                            'path': item['path'],
                            'relevance_score': relevance_score,
                            'repository': DOCUMENTATION_REPO
                        })

            # Sort by relevance score
            search_results.sort(key=lambda x: x['relevance_score'], reverse=True)

            # Update rank order after sorting
            for i, result in enumerate(search_results):
                result['rank_order'] = i + 1

            return search_results[:limit]

        return []

    except Exception as e:
        logger.error(f"Error searching Amplify documentation: {e}")
        return []

def calculate_relevance_score_from_path(path: str, query: str) -> float:
    """Calculate relevance score for search results based on file path only."""
    score = 0.0
    path_lower = path.lower()
    query_lower = query.lower()

    # Higher score for exact matches in filename
    filename = path_lower.split('/')[-1]
    if query_lower in filename:
        score += 10.0

    # Score for matches in path components
    path_components = path_lower.split('/')
    for component in path_components:
        if query_lower in component:
            score += 5.0

    # Boost for Gen2 specific content
    if 'gen2' in path_lower or 'gen-2' in path_lower:
        score += 3.0

    # Boost for framework-specific content
    frameworks = ['react', 'vue', 'angular', 'nextjs', 'flutter']
    for framework in frameworks:
        if framework in path_lower:
            score += 2.0

    # Boost for core topics
    core_topics = ['auth', 'data', 'storage', 'function', 'api', 'deploy']
    for topic in core_topics:
        if topic in path_lower:
            score += 2.0

    # Boost for build-a-backend content (Gen2 specific)
    if 'build-a-backend' in path_lower:
        score += 4.0

    # Boost for pages directory (main content)
    if '/pages/' in path_lower:
        score += 1.0

    return score

def calculate_relevance_score(item: Dict, query: str) -> float:
    """Calculate relevance score for search results."""
    score = 0.0
    path = item['path'].lower()
    query_lower = query.lower()

    # Higher score for exact matches in filename
    filename = path.split('/')[-1]
    if query_lower in filename:
        score += 10.0

    # Score for matches in path components
    path_components = path.split('/')
    for component in path_components:
        if query_lower in component:
            score += 5.0

    # Boost for Gen2 specific content
    if 'gen2' in path or 'gen-2' in path:
        score += 3.0

    # Boost for framework-specific content
    frameworks = ['react', 'vue', 'angular', 'nextjs', 'flutter']
    for framework in frameworks:
        if framework in path:
            score += 2.0

    # Boost for core topics
    core_topics = ['auth', 'data', 'storage', 'function', 'api', 'deploy']
    for topic in core_topics:
        if topic in path:
            score += 2.0

    return score

def extract_title_from_path(path: str) -> str:
    """Extract a readable title from file path."""
    filename = path.split('/')[-1].replace('.md', '').replace('.mdx', '')

    # Convert kebab-case and snake_case to title case
    title = filename.replace('-', ' ').replace('_', ' ')
    title = ' '.join(word.capitalize() for word in title.split())

    # Add context from parent directories
    path_parts = path.split('/')[:-1]  # Exclude filename
    if len(path_parts) > 0:
        context = ' - '.join(part.replace('-', ' ').title() for part in path_parts[-2:])
        title = f"{title} ({context})"

    return title

def fetch_github_content(repo: str, path: str, branch: str = "main") -> Optional[str]:
    """Fetch content from a GitHub repository file.

    Args:
        repo: Repository in format "owner/repo"
        path: Path to the file in the repository
        branch: Branch name (default: "main")

    Returns:
        File content as string, or None if not found
    """
    try:
        url = f"{GITHUB_API_BASE}/repos/{repo}/contents/{path}"
        params = {"ref": branch}

        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'AmplifyGen2MCPServer/1.0'
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            content_data = response.json()
            if content_data.get('encoding') == 'base64':
                content = base64.b64decode(content_data['content']).decode('utf-8')
                return content

        return None

    except Exception as e:
        logger.error(f"Error fetching GitHub content from {repo}/{path}: {e}")
        return None

def fetch_raw_content(raw_url: str) -> Optional[str]:
    """Fetch content from a raw GitHub URL.

    Args:
        raw_url: Raw GitHub URL

    Returns:
        File content as string, or None if not found
    """
    try:
        headers = {
            'User-Agent': 'AmplifyGen2MCPServer/1.0'
        }

        response = requests.get(raw_url, headers=headers, timeout=10)

        if response.status_code == 200:
            return response.text

        return None

    except Exception as e:
        logger.error(f"Error fetching raw content from {raw_url}: {e}")
        return None

def discover_project_templates(framework: str = None) -> Dict[str, Any]:
    """Search Amplify Gen2 documentation comprehensively.

    Args:
        ctx: MCP context
        query: Search query string
        limit: Maximum number of results to return

    Returns:
        Comprehensive search results from official documentation and samples
    """
    logger.info(f"Searching Amplify Gen2 documentation for: {query}")

    # Search official documentation
    doc_results = search_amplify_documentation(query, limit)

    # Search sample repositories
    sample_results = search_sample_repositories(query)

    # Format results
    result = f"""
# Amplify Gen2 Documentation Search Results

**Query:** {query}
**Found:** {len(doc_results)} documentation results, {len(sample_results)} code examples

## Official Documentation

"""

    if doc_results:
        for i, result_item in enumerate(doc_results[:limit], 1):
            result += f"""
### {i}. {result_item['title']}
**URL:** {result_item['url']}
**Path:** {result_item['path']}
**Relevance Score:** {result_item['relevance_score']:.1f}

"""
    else:
        result += "No documentation results found.\n\n"

    result += "## Code Examples\n\n"

    if sample_results:
        for i, sample in enumerate(sample_results[:5], 1):
            result += f"""
### {i}. {sample['title']}
**Framework:** {sample['framework'].title()}
**Repository:** https://github.com/{sample['repository']}
**File:** {sample['path']}
**URL:** {sample['url']}

"""
    else:
        result += "No code examples found.\n\n"

    result += """
## Next Steps

1. **Read Documentation:** Click on the documentation URLs above to read the full content
2. **Explore Code:** Visit the repository URLs to see complete implementation examples
3. **Get Content:** Use the read_amplify_documentation tool with specific URLs for full content

**Available Search Topics:**
- Authentication, authorization, sign-in, sign-up, MFA
- Data modeling, GraphQL, API, database, schema
- Storage, file upload, S3, media
- Functions, Lambda, serverless, API
- Deployment, hosting, CI/CD, environments
- AI, machine learning, Bedrock, generation
- Analytics, monitoring, logging
- Push notifications, real-time, subscriptions

**Available Frameworks:** React, Vue, Angular, Next.js, Flutter
    """

    return result