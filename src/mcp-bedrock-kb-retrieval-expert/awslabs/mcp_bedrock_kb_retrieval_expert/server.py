"""mcp-bedrock-kb-retrieval-expert MCP server implementation."""

import argparse
import json
import os
import sys
from awslabs.mcp_bedrock_kb_retrieval_expert.knowledgebases.clients import (
    get_bedrock_agent_client,
    get_bedrock_agent_runtime_client,
)
from awslabs.mcp_bedrock_kb_retrieval_expert.knowledgebases.discovery import (
    discover_knowledge_bases,
)
from awslabs.mcp_bedrock_kb_retrieval_expert.knowledgebases.runtime import (
    query_knowledge_base,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import List, Literal, Optional


logger.remove(0)
logger.add(sys.stderr, level='INFO')


global kb_runtime_client
global kb_agent_mgmt_client

try:
    kb_runtime_client = get_bedrock_agent_runtime_client(profile_name=os.getenv('AWS_PROFILE'))
    kb_agent_mgmt_client = get_bedrock_agent_client(profile_name=os.getenv('AWS_PROFILE'))
except Exception as e:
    logger.error(f'Error getting bedrock agent client: {e}')
    raise e


mcp = FastMCP(
    'awslabs.mcp-bedrock-kb-retrieval-expert',
    instructions="""
    The AWS Labs Bedrock Knowledge Bases Expert provides access to Amazon Bedrock Knowledge Bases for retrieving relevant information through natural language queries.

    ## Usage Workflow:
    1. ALWAYS start by accessing the `resource://knowledgebases` resource to discover available knowledge bases and their data sources
    2. Use the QueryKnowledgeBases tool to search specific knowledge bases with your natural language queries
    3. You can make multiple calls to QueryKnowledgeBases with different queries or targeting different knowledge bases

    ## Important Notes:
    - Knowledge bases contain structured data from various data sources (documents, websites, databases)
    - Each knowledge base has a unique ID that must be used when querying
    - You can filter by specific data sources within a knowledge base using data_source_ids
    - Always verify that the knowledge base ID exists in the resource response before querying
    """,
    dependencies=['boto3'],
)


@mcp.resource(uri='resource://knowledgebases', name='KnowledgeBases', mime_type='application/json')
async def knowledgebases_resource() -> str:
    """List all available Amazon Bedrock Knowledge Bases and their data sources.

    This resource returns a mapping of knowledge base IDs to their details, including:
    - name: The human-readable name of the knowledge base
    - data_sources: A list of data sources within the knowledge base, each with:
      - id: The unique identifier of the data source
      - name: The human-readable name of the data source

    ## Example response structure:
    ```json
    {
        "kb-12345": {
            "name": "Customer Support KB",
            "data_sources": [
                {"id": "ds-abc123", "name": "Technical Documentation"},
                {"id": "ds-def456", "name": "FAQs"}
            ]
        },
        "kb-67890": {
            "name": "Product Information KB",
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
    return json.dumps(await discover_knowledge_bases(kb_agent_mgmt_client))


@mcp.tool(name='QueryKnowledgeBases')
async def query_knowledge_bases_tool(
    query: str = Field(
        ..., description='A natural language query to search the knowledge base with'
    ),
    knowledge_base_id: str = Field(
        ...,
        description='The knowledge base ID to query. It must be a valid ID from the resource://knowledgebases MCP resource',
    ),
    number_of_results: int = Field(
        10,
        description='The number of results to return. Use smaller values for focused results and larger values for broader coverage.',
    ),
    reranking: bool = Field(
        True,
        description='Whether to rerank the results. Useful for improving relevance and sorting.',
    ),
    reranking_model_name: Literal['COHERE', 'AMAZON'] = Field(
        'AMAZON', description="The name of the reranking model to use. Options: 'COHERE', 'AMAZON'"
    ),
    data_source_ids: Optional[List[str]] = Field(
        None,
        description='The data source IDs to filter the knowledge base by. It must be a list of valid data source IDs from the resource://knowledgebases MCP resource',
    ),
) -> str:
    """Query an Amazon Bedrock Knowledge Base using natural language.

    ## Usage Requirements
    - You MUST first use the `resource://knowledgebases` resource to get valid knowledge base IDs
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
    )


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(description='A Model Context Protocol (MCP) server')
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':
    main()
