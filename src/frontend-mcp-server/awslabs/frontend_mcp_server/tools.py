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
import os
import httpx
from datetime import datetime, timedelta
from .consts import (
    DEFAULT_SEARCH_LIMIT,
    DOCUMENTATION_REPO,
    GITHUB_API_BASE,
    PROJECT_TEMPLATE_FILES,
    SAMPLE_REPOSITORIES,
)
from typing import Any, Dict, List, Optional


async def search_amplify_documentation(query: str, limit: int = DEFAULT_SEARCH_LIMIT) -> List[Dict]:
    """Search Amplify documentation using GitHub API first, fallback to docs site.

    Args:
        query: Search query string
        limit: Maximum number of results to return

    Returns:
        List of search results with file information and relevance
    """
    # Try GitHub API first
    github_results = await search_github_docs(query, limit)
    if github_results:
        return github_results
    
    # Fallback to Amplify docs site
    return await search_amplify_docs_site(query, limit)


async def search_github_docs(query: str, limit: int) -> List[Dict]:
    """Search GitHub repository for documentation."""
    try:
        tree_url = f"{GITHUB_API_BASE}/repos/{DOCUMENTATION_REPO}/git/trees/main?recursive=1"
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'AmplifyGen2MCPServer/1.0'
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(tree_url, headers=headers)

            if response.status_code == 403:
                print("GitHub rate limit exceeded, falling back to docs site")
                return []
            
            if response.status_code == 200:
                tree_data = response.json()
                search_results = []

                for item in tree_data.get('tree', []):
                    if item['type'] == 'blob' and item['path'].endswith(('.md', '.mdx')):
                        relevance_score = calculate_relevance_score_from_path(item['path'], query)

                        if relevance_score > 0:
                            search_results.append({
                                'rank_order': len(search_results) + 1,
                                'url': f"https://github.com/{DOCUMENTATION_REPO}/blob/main/{item['path']}",
                                'raw_url': f"https://raw.githubusercontent.com/{DOCUMENTATION_REPO}/main/{item['path']}",
                                'title': extract_title_from_path(item['path']),
                                'path': item['path'],
                                'relevance_score': relevance_score,
                                'repository': DOCUMENTATION_REPO,
                                'source': 'github'
                            })

                search_results.sort(key=lambda x: x['relevance_score'], reverse=True)
                for i, result in enumerate(search_results):
                    result['rank_order'] = i + 1

                return search_results[:limit]

        return []

    except Exception as e:
        print(f"GitHub search error: {e}")
        return []


async def search_amplify_docs_site(query: str, limit: int) -> List[Dict]:
    """Search Amplify docs site using sitemap."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://docs.amplify.aws/sitemap.xml")
            
            if response.status_code != 200:
                return []
            
            # Parse XML sitemap
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            
            search_results = []
            query_lower = query.lower()
            
            for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                loc_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc_elem is not None:
                    url = loc_elem.text
                    path = url.replace('https://docs.amplify.aws/', '')
                    
                    # Filter for relevant pages and calculate relevance
                    if '/gen2/' in path or '/react/' in path or '/nextjs/' in path:
                        relevance_score = calculate_sitemap_relevance(path, query_lower)
                        
                        if relevance_score > 0:
                            search_results.append({
                                'rank_order': len(search_results) + 1,
                                'url': url,
                                'title': extract_title_from_url(path),
                                'path': path,
                                'relevance_score': relevance_score,
                                'source': 'sitemap'
                            })
            
            # Sort by relevance and limit results
            search_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            for i, result in enumerate(search_results):
                result['rank_order'] = i + 1
                
            return search_results[:limit]
            
    except Exception as e:
        print(f"Sitemap search error: {e}")
        return []


def calculate_sitemap_relevance(path: str, query: str) -> float:
    """Calculate relevance for sitemap URLs."""
    score = 0.0
    path_lower = path.lower()
    
    # Exact match in path
    if query in path_lower:
        score += 10.0
    
    # Partial matches
    query_words = query.split()
    for word in query_words:
        if word in path_lower:
            score += 5.0
    
    # Boost for Gen2 content
    if 'gen2' in path_lower:
        score += 3.0
        
    # Boost for core topics
    core_topics = ['auth', 'data', 'storage', 'function', 'api']
    for topic in core_topics:
        if topic in path_lower and topic in query:
            score += 8.0
            
    return score


def extract_title_from_url(path: str) -> str:
    """Extract readable title from URL path."""
    # Remove leading slash and split by /
    parts = path.strip('/').split('/')
    
    if len(parts) >= 3:
        # Format: framework/section/topic
        framework = parts[0].title()
        section = parts[-1].replace('-', ' ').title()
        return f"{section} ({framework})"
    
    # Fallback to last part
    return parts[-1].replace('-', ' ').title() if parts else "Documentation"

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

async def fetch_github_content(repo: str, path: str, branch: str = "main") -> Optional[str]:
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

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers, params=params)

            if response.status_code == 200:
                content_data = response.json()
                if content_data.get('encoding') == 'base64':
                    content = base64.b64decode(content_data['content']).decode('utf-8')
                    return content

        return None

    except Exception as e:
        print(f"Error fetching GitHub content from {repo}/{path}: {e}")
        return None

async def fetch_raw_content(raw_url: str) -> Optional[str]:
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

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(raw_url, headers=headers)

            if response.status_code == 200:
                return response.text

        return None

    except Exception as e:
        print(f"Error fetching raw content from {raw_url}: {e}")
        return None

async def search_sample_repositories(query: str) -> List[Dict]:
    """Search sample repositories for code examples.
    
    Args:
        query: Search query string
        
    Returns:
        List of sample repository results
    """
    # For now, return empty list as this feature is not fully implemented
    # This prevents the function from crashing when called
    return []