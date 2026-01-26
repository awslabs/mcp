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

"""AgentCore documentation search and retrieval tools."""
import logging
from mcp.server.fastmcp import Context
from ..utils import cache, text_processor
from typing import Any, Dict, List

logger = logging.getLogger('amazon-bedrock-mcp.docs')

async def search_agentcore_docs(query: str, k: int = 5, ctx: Context = None) -> List[Dict[str, Any]]:
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
    logger.info(f"Initiating document search: '{query}' (top-k: {k})")
    if ctx:
        await ctx.info(f"Searching AgentCore docs for: '{query}'...")

    logger.debug("Checking search cache integrity...")
    cache.ensure_ready()
    
    index = cache.get_index()
    results = index.search(query, k=k) if index else []
    url_cache = cache.get_url_cache()

   # Hydration Process (may be slow, so we notify the user)
    top = results[: min(len(results), cache.SNIPPET_HYDRATE_MAX)]
    if top:
        logger.info(f"Hydrating {len(top)} results for snippet extraction.")
        if ctx:
            await ctx.info(f"Extracting snippets from {len(top)} relevant pages...")
            
        for _, doc in top:
            cached = url_cache.get(doc.uri)
            if cached is None or not cached.content:
                logger.debug(f"Hydrating page: {doc.uri}")
                cache.ensure_page(doc.uri)

    # Response construction
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
    
    logger.info(f"Search finished. {len(return_docs)} results found.")
    return return_docs

async def fetch_agentcore_doc(uri: str, ctx: Context = None) -> Dict[str, Any]:
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
    logger.info(f"Request for full content: {uri}")
    if ctx:
        await ctx.info(f"Fetching full content from: {uri}")

    cache.ensure_ready()

    try:
        page = cache.ensure_page(uri)
        if page is None:
            error_msg = f"Failed to retrieve the page: {uri}"
            logger.error(error_msg)
            if ctx:
                await ctx.error(error_msg)
            return {'error': 'fetch failed', 'url': uri}

        logger.info(f"Document '{page.title}' successfully recovered.")
        return {
            'url': page.url,
            'title': page.title,
            'content': page.content,
        }
    except Exception as e:
        logger.exception(f"Unexpected error while searching for document. {uri}: {str(e)}")
        if ctx:
            await ctx.error(f"Error fetching document: {str(e)}")
        return {'error': str(e), 'url': uri}
