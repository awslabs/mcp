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

"""awslabs {{cookiecutter.project_domain}} MCP Server implementation."""

from .utils import cache, text_processor
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List


APP_NAME = '{{cookiecutter.project_domain | lower | replace(" ", "-") | replace("_", "-")}}-mcp-server'
mcp = FastMCP(APP_NAME)


@mcp.tool()
def {{cookiecutter.search_tool_name}}(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """Search curated {{cookiecutter.project_domain}} documentation and return ranked results with snippets.

    This tool provides access to the complete {{cookiecutter.project_domain}} documentation including:

    **Platform Overview:**
    - What is {{cookiecutter.project_domain}}, security overview, quotas and limits

    **Core Services:**
    - Service documentation and API references
    - Getting started guides and tutorials
    - Best practices and examples
    - Integration guides and troubleshooting

    **Development Resources:**
    - Prerequisites & environment setup
    - Building your first application
    - Local development & testing
    - Deployment and configuration
    - API reference documentation

    **Examples & Tutorials:**
    - Basic usage examples
    - Advanced integration patterns
    - Error handling and debugging
    - Performance optimization

    Use this to find relevant {{cookiecutter.project_domain}} documentation for any development question.

    Args:
        query: Search query string (e.g., "{{cookiecutter.project_domain | lower}}", "getting started", "api reference")
        k: Maximum number of results to return (default: 5)

    Returns:
        List of dictionaries containing:
        - url: Document URL
        - title: Display title
        - score: Relevance score (0-1, higher is better)
        - snippet: Contextual content preview

    """
    cache.ensure_ready()
    index = cache.get_index()
    results = index.search(query, k=k) if index else []
    url_cache = cache.get_url_cache()

    # Fetch content for all results to enable content-aware ranking
    for _, doc in results:
        cache.ensure_page(doc.uri)
    
    # Re-rank with content now available
    if index:
        results = index.search(query, k=k)

    # Build response with real content snippets when available
    return_docs: List[Dict[str, Any]] = []
    for score, doc in results:
        page = url_cache.get(doc.uri)
        snippet = text_processor.make_snippet(page, doc.display_title)
        return_docs.append(
            {
                'url': doc.uri,
                'title': doc.display_title,
                'score': round(score, 3),
                'snippet': snippet,
            }
        )
    return return_docs


@mcp.tool()
def {{cookiecutter.fetch_tool_name}}(uri: str) -> Dict[str, Any]:
    """Fetch full document content by URL.

    Retrieves complete {{cookiecutter.project_domain}} documentation content from URLs found via {{cookiecutter.search_tool_name}}
    or provided directly. Use this to get full documentation pages including:

    - Complete platform overview and service documentation
    - Detailed getting started guides with step-by-step instructions
    - Full API reference documentation
    - Comprehensive tutorial and example code
    - Complete deployment and configuration instructions
    - Integration guides for various frameworks and tools

    This provides the full content when search snippets aren't sufficient for
    understanding or implementing {{cookiecutter.project_domain}} features.

    Args:
        uri: Document URI (supports http/https URLs)

    Returns:
        Dictionary containing:
        - url: Canonical document URL
        - title: Document title
        - content: Full document text content
        - error: Error message (if fetch failed)

    """
    cache.ensure_ready()

    page = cache.ensure_page(uri)
    if page is None:
        return {'error': 'fetch failed', 'url': uri}

    return {
        'url': page.url,
        'title': page.title,
        'content': page.content,
    }


def main() -> None:
    """Main entry point for the MCP server.

    Initializes the document cache and starts the FastMCP server.
    The cache is loaded with document titles only for fast startup,
    with full content fetched on-demand.
    """
    cache.ensure_ready()
    mcp.run()


if __name__ == '__main__':
    main()
