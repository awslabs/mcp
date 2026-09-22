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
"""awslabs Bedrock Knowledge Base Retrieval MCP Server."""

import json
import os
import sys
from awslabs.bedrock_kb_retrieval_mcp_server.knowledgebases.agentic import (
    agentic_retrieve_knowledge_bases,
)
from awslabs.bedrock_kb_retrieval_mcp_server.knowledgebases.clients import (
    get_bedrock_agent_client,
    get_bedrock_agent_runtime_client,
)
from awslabs.bedrock_kb_retrieval_mcp_server.knowledgebases.discovery import (
    DEFAULT_KNOWLEDGE_BASE_TAG_INCLUSION_KEY,
    discover_knowledge_bases,
)
from awslabs.bedrock_kb_retrieval_mcp_server.knowledgebases.retrieval import (
    query_knowledge_base,
)
from loguru import logger
from mcp.server.mcpserver import MCPServer
from pydantic import Field
from typing import List, Literal, Optional


# Remove all default handlers then add our own
logger.remove()
logger.add(sys.stderr, level='INFO')


global kb_runtime_client
global kb_agent_mgmt_client

try:
    kb_runtime_client = get_bedrock_agent_runtime_client(
        region_name=os.getenv('AWS_REGION'),
        profile_name=os.getenv('AWS_PROFILE'),
    )
    kb_agent_mgmt_client = get_bedrock_agent_client(
        region_name=os.getenv('AWS_REGION'),
        profile_name=os.getenv('AWS_PROFILE'),
    )
except Exception as e:
    logger.error(f'Error getting bedrock agent client: {e}')
    raise e

kb_inclusion_tag_key = os.getenv('KB_INCLUSION_TAG_KEY', DEFAULT_KNOWLEDGE_BASE_TAG_INCLUSION_KEY)

# Parse reranking enabled environment variable
kb_reranking_enabled_raw = os.getenv('BEDROCK_KB_RERANKING_ENABLED')
kb_reranking_enabled = False  # Default value is now False (off)
if kb_reranking_enabled_raw is not None:
    kb_reranking_enabled_raw = kb_reranking_enabled_raw.strip().lower()
    if kb_reranking_enabled_raw in ('true', '1', 'yes', 'on'):
        kb_reranking_enabled = True
logger.info(
    f'Default reranking enabled: {kb_reranking_enabled} (from BEDROCK_KB_RERANKING_ENABLED)'
)

mcp = MCPServer(
    'awslabs.bedrock-kb-retrieval-mcp-server',
    instructions="""
    The AWS Labs Bedrock Knowledge Bases Retrieval MCP Server provides access to Amazon Bedrock Knowledge Bases for retrieving relevant information through natural language queries.

    ## Usage Workflow:
    1. ALWAYS start by using the ListKnowledgeBases tool to discover available knowledge bases, their data sources, and their type
    2. Use the QueryKnowledgeBases tool to search specific knowledge bases with your natural language queries
    3. You can make multiple calls to QueryKnowledgeBases with different queries or targeting different knowledge bases
    4. For MANAGED knowledge bases, the AgenticQueryKnowledgeBases tool can plan a multi-step retrieval and synthesise a cited answer. Prefer it for questions needing reasoning across several data sources; it invokes a foundation model and so costs more per call than QueryKnowledgeBases.

    ## Important Notes:
    - Knowledge bases contain structured data from various data sources (documents, websites, databases)
    - Each knowledge base has a unique ID that must be used when querying
    - You can filter by specific data sources within a knowledge base using data_source_ids
    - Always verify that the knowledge base ID exists in the ListKnowledgeBases tool response before querying
    """,
    dependencies=['boto3'],
)


@mcp.tool(name='ListKnowledgeBases')
async def list_knowledge_bases_tool() -> str:
    """List all available Amazon Bedrock Knowledge Bases and their data sources.

    This tool returns a mapping of knowledge base IDs to their details, including:
    - name: The human-readable name of the knowledge base
    - description: The description of the knowledge base
    - data_sources: A list of data sources within the knowledge base, each with:
      - id: The unique identifier of the data source
      - name: The human-readable name of the data source

    ## Example response structure:
    ```json
    {
        "kb-12345": {
            "name": "Customer Support KB",
            "description": "Knowledge base containing customer support documentation and FAQs",
            "data_sources": [
                {"id": "ds-abc123", "name": "Technical Documentation"},
                {"id": "ds-def456", "name": "FAQs"}
            ]
        },
        "kb-67890": {
            "name": "Product Information KB",
            "description": "Comprehensive product specifications and details",
            "data_sources": [
                {"id": "ds-ghi789", "name": "Product Specifications"}
            ]
        }
    }
    ```

    ## How to use this information:
    1. Extract the knowledge base IDs (like "kb-12345") for use with the QueryKnowledgeBases tool
    2. Note the data source IDs if you want to filter queries to specific data sources
    3. Use the names to determine which knowledge base and data source(s) are most relevant to the user's query
    """
    knowledge_bases = await discover_knowledge_bases(kb_agent_mgmt_client, kb_inclusion_tag_key)
    return json.dumps(knowledge_bases)


@mcp.tool(name='QueryKnowledgeBases')
async def query_knowledge_bases_tool(
    query: str = Field(
        ..., description='A natural language query to search the knowledge base with'
    ),
    knowledge_base_id: str = Field(
        ...,
        description='The knowledge base ID to query. It must be a valid ID from the ListKnowledgeBases tool',
    ),
    number_of_results: int = Field(
        10,
        description='The number of results to return. Use smaller values for focused results and larger values for broader coverage.',
    ),
    reranking: bool = Field(
        kb_reranking_enabled,
        description='Whether to rerank the results. Useful for improving relevance and sorting. Can be globally configured with BEDROCK_KB_RERANKING_ENABLED environment variable.',
    ),
    reranking_model_name: Literal['COHERE', 'AMAZON'] = Field(
        'AMAZON',
        description="The name of the reranking model to use. Options: 'COHERE', 'AMAZON'",
    ),
    data_source_ids: Optional[List[str]] = Field(
        None,
        description='The data source IDs to filter the knowledge base by. It must be a list of valid data source IDs from the ListKnowledgeBases tool',
    ),
    user_id: Optional[str] = Field(
        None,
        description='End-user identity for access-control filtering. Required to reach content in ACL-aware data sources such as SharePoint, OneDrive or Confluence with per-document ACLs; that content is otherwise inaccessible. Omit for data sources without ACLs.',
    ),
) -> str:
    """Query an Amazon Bedrock Knowledge Base using natural language.

    ## Usage Requirements
    - You MUST first use the ListKnowledgeBases tool to get valid knowledge base IDs
    - You can query different knowledge bases or make multiple queries to the same knowledge base

    ## Query Tips
    - Use clear, specific natural language queries for best results
    - You can use this tool MULTIPLE TIMES with different queries to gather comprehensive information
    - Break complex questions into multiple focused queries
    - Consider querying for factual information and explanations separately

    ## Tool output format
    The response contains multiple JSON objects (one per line), each representing a retrieved document with:
    - content: The text content of the document
    - location: The source location of the document
    - score: The relevance score of the document


    ## Interpretation Best Practices
    1. Extract and combine key information from multiple results
    2. Consider the source and relevance score when evaluating information
    3. Use follow-up queries to clarify ambiguous or incomplete information
    4. If the response is not relevant, try a different query, knowledge base, and/or data source
    5. After a few attempts, ask the user for clarification or a different query.
    """
    return await query_knowledge_base(
        query=query,
        knowledge_base_id=knowledge_base_id,
        kb_agent_client=kb_runtime_client,
        number_of_results=number_of_results,
        reranking=reranking,
        reranking_model_name=reranking_model_name,
        data_source_ids=data_source_ids,
        kb_agent_mgmt_client=kb_agent_mgmt_client,
        user_id=user_id,
    )


@mcp.tool(name='AgenticQueryKnowledgeBases')
async def agentic_query_knowledge_bases_tool(
    query: str = Field(
        ..., description='A natural language question to answer from the knowledge bases'
    ),
    knowledge_base_ids: List[str] = Field(
        ...,
        description='Managed knowledge base IDs to search. Must be IDs from the ListKnowledgeBases tool whose "type" is MANAGED. More than one may be given, and the agent decides which to search.',
    ),
    generate_response: bool = Field(
        True,
        description='Whether to synthesise a cited answer from the retrieved results. Set false to get results only, which is faster and cheaper.',
    ),
    number_of_results: Optional[int] = Field(
        None, description='Maximum number of results per knowledge base.'
    ),
    data_source_ids: Optional[List[str]] = Field(
        None,
        description='Restrict retrieval to these data source IDs, from the ListKnowledgeBases tool.',
    ),
    max_agent_iterations: Optional[int] = Field(
        None, description='Cap on the agent planning iterations (minimum 2).'
    ),
    include_trace: bool = Field(
        False,
        description="Include a condensed per-step trace of the agent's planning and retrieval. Useful for debugging why results were or were not found.",
    ),
    user_id: Optional[str] = Field(
        None,
        description='End-user identity for access-control filtering. Required to reach content in ACL-aware data sources such as SharePoint, OneDrive or Confluence with per-document ACLs; that content is otherwise inaccessible. Omit for data sources without ACLs.',
    ),
    next_token: Optional[str] = Field(
        None,
        description="Continuation token from a previous call's `nextToken`, to fetch the next page of results.",
    ),
) -> str:
    """Answer a question from Amazon Bedrock **managed** knowledge bases using agentic retrieval.

    Agentic retrieval plans a strategy, runs one or more searches across the knowledge
    bases you give it, and optionally synthesises an answer with citations. Prefer it over
    QueryKnowledgeBases for questions that need multi-step reasoning, span several data
    sources or knowledge bases, or benefit from a written answer rather than raw passages.

    ## Usage Requirements
    - You MUST first use the ListKnowledgeBases tool to get valid knowledge base IDs
    - This tool supports MANAGED knowledge bases only. For a knowledge base whose `type`
      is not MANAGED, use QueryKnowledgeBases instead.

    ## Choosing between this tool and QueryKnowledgeBases
    - QueryKnowledgeBases: a single search, returns ranked passages. Cheaper and faster.
    - AgenticQueryKnowledgeBases: multi-step planning, optional synthesised answer with
      citations. Invokes a foundation model, so it costs more per call.

    ## Tool output format
    A single JSON object:
    - `results`: retrieved items, each with `index`, `text`, `mimeType`, `metadata` and
      `knowledgeBaseId`
    - `answer`: the synthesised answer (only when `generate_response` is true)
    - `citations`: spans of the answer mapped to `resultIndexes` into `results`
    - `trace`: condensed per-step trace (only when `include_trace` is true)
    - `warnings` / `failures` / `nextToken`: present only when non-empty

    ## Interpretation Best Practices
    1. When an answer is present, use the citations to attribute claims to specific results
    2. Cross-check the answer against the `results` text rather than trusting it blindly
    3. If results are empty, retry with `include_trace=true` to see what the agent searched
    4. Narrow with `data_source_ids` when you know which source should hold the answer
    """
    return await agentic_retrieve_knowledge_bases(
        query=query,
        knowledge_base_ids=knowledge_base_ids,
        kb_agent_client=kb_runtime_client,
        kb_agent_mgmt_client=kb_agent_mgmt_client,
        generate_response=generate_response,
        number_of_results=number_of_results,
        data_source_ids=data_source_ids,
        max_agent_iterations=max_agent_iterations,
        include_trace=include_trace,
        user_id=user_id,
        next_token=next_token,
    )


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == '__main__':
    main()
