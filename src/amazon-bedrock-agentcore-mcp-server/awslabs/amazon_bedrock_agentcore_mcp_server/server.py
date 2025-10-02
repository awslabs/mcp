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

"""awslabs AWS Bedrock AgentCore MCP Server implementation."""

from .utils import cache, text_processor
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List


APP_NAME = 'amazon-bedrock-agentcore-mcp-server'
mcp = FastMCP(APP_NAME)


@mcp.tool()
def search_agentcore_docs(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """Search curated AgentCore documentation and return ranked results with snippets.

    This tool provides access to the complete Amazon Bedrock AgentCore documentation including:

    **Platform Overview:**
    - What is Bedrock AgentCore, security overview, quotas and limits

    **Platform Services:**
    - AgentCore Runtime (serverless deployment and scaling)
    - AgentCore Memory (persistent knowledge with event and semantic memory)
    - AgentCore Code Interpreter (secure code execution in isolated sandboxes)
    - AgentCore Browser (fast, secure cloud-based browser for web interaction)
    - AgentCore Gateway (transform existing APIs into agent tools)
    - AgentCore Observability (real-time monitoring and tracing)
    - AgentCore Identity (secure authentication and access management)

    **Getting Started:**
    - Prerequisites & environment setup
    - Building your first agent or transforming existing code
    - Local development & testing
    - Deployment to AgentCore using CLI
    - Troubleshooting & enhancement

    **Examples & Tutorials:**
    - Basic agent creation, memory integration, tool usage
    - Streaming responses, error handling, authentication
    - Customer service agents, code review assistants, data analysis
    - Multi-agent workflows and integrations

    **API Reference:**
    - Data plane and control API documentation

    Use this to find relevant AgentCore documentation for any development question.

    Args:
        query: Search query string (e.g., "bedrock agentcore", "memory integration", "deployment guide")
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

    # Collect top-k URLs that need hydration (no content yet)
    # Simplified: Direct hydration in one pass
    top = results[: min(len(results), cache.SNIPPET_HYDRATE_MAX)]
    for _, doc in top:
        cached = url_cache.get(doc.uri)
        if cached is None or not cached.content:
            cache.ensure_page(doc.uri)

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
def fetch_agentcore_doc(uri: str) -> Dict[str, Any]:
    """Fetch full document content by URL.

    Retrieves complete AgentCore documentation content from URLs found via search_agentcore_docs
    or provided directly. Use this to get full documentation pages including:

    - Complete platform overview and service documentation
    - Detailed getting started guides with step-by-step instructions
    - Full API reference documentation
    - Comprehensive tutorial and example code
    - Complete deployment and configuration instructions
    - Integration guides for various frameworks (Strands, LangGraph, CrewAI, etc.)

    This provides the full content when search snippets aren't sufficient for
    understanding or implementing AgentCore features.

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
