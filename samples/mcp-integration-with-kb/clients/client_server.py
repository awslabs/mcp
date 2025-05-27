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

import boto3
import logging
import os
import sys
import traceback
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from langchain.schema.messages import HumanMessage, ToolMessage
from langchain_aws import ChatBedrock
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel
from typing import Any, Dict, List


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

SYSTEM_PROMPT = """You're a helpful assistant that has access to various tools. Your job is to understand if it is necessary to use these tools to carry out a user's request or respond without them. If you do find the need to use tools, request the tools. If you receive a tool result, then process the results then return a normal output.

When using the query_knowledge_base tool, always use the kb_id parameter exactly as provided by the system. Do not hardcode or guess the kb_id value."""

# Initialize Bedrock client
try:
    bedrock_runtime = boto3.client(
        service_name='bedrock-runtime',
        region_name=os.getenv('AWS_REGION', 'us-west-2'),
    )
    logger.info('Successfully initialized Bedrock client')
except Exception as e:
    logger.error(f'Failed to initialize Bedrock client: {str(e)}')
    bedrock_runtime = None

# Initialize FastAPI app
app = FastAPI(title='Bedrock KB Assistant API')


# Add exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions in the FastAPI application."""
    logger.error(f'Global exception: {str(exc)}')
    logger.error(traceback.format_exc())
    return JSONResponse(status_code=500, content={'detail': f'An error occurred: {str(exc)}'})


# Define request/response models
class QueryRequest(BaseModel):
    """Request model for querying the knowledge base."""

    query: str
    kb_id: str


class QueryResponse(BaseModel):
    """Response model containing messages from the knowledge base query."""

    messages: List[Dict[str, Any]]


class KnowledgeBaseRequest(BaseModel):
    """Request model for knowledge base operations."""

    kb_id: str


class KnowledgeBaseResponse(BaseModel):
    """Response model for knowledge base operations."""

    message: str
    kb_id: str


# Connect to the MCP server and create an agent
async def process_query(query: str, kb_id: str) -> Dict[str, Any]:
    """Process a query using the Bedrock KB through MCP server.

    Args:
        query: The user's query
        kb_id: The knowledge base ID to query

    Returns:
        A dictionary with the processed messages
    """
    logger.info(f"Processing query: '{query}' for KB ID: {kb_id}")

    try:
        # Initialize MCP client using the awslabs.bedrock-kb-retrieval-mcp-server
        logger.info('Initializing MCP client with awslabs.bedrock-kb-retrieval-mcp-server')
        mcp_client = MultiServerMCPClient(
            {
                'bedrock_kb': {
                    'transport': 'stdio',
                    'command': 'uvx',
                    'args': ['awslabs.bedrock-kb-retrieval-mcp-server@latest'],
                    'env': {
                        'AWS_PROFILE': os.getenv('AWS_PROFILE', 'default'),
                        'AWS_REGION': os.getenv('AWS_REGION', 'us-west-2'),
                        'FASTMCP_LOG_LEVEL': 'ERROR',
                    },
                }
            }
        )

        # Create a Bedrock LLM
        logger.info('Creating Bedrock LLM')
        if not bedrock_runtime:
            raise ValueError('Bedrock client is not initialized')

        # Get tools from the MCP server
        logger.info('Getting tools from MCP server')
        tools = await mcp_client.get_tools()
        logger.info(
            f'Retrieved {len(tools)} tools from MCP server: {[tool.name for tool in tools]}'
        )

        if not tools:
            logger.warning('No tools were returned from the MCP server')
            return {
                'messages': [{'content': 'No tools available from the knowledge base server.'}]
            }

        # Create a ChatBedrock instance with tools
        logger.info('Creating ChatBedrock with tools')
        chat_model = ChatBedrock(
            client=bedrock_runtime,
            model_id='anthropic.claude-3-sonnet-20240229-v1:0',
            model_kwargs={
                'temperature': 0.7,
                'max_tokens': 2048,
                'anthropic_version': 'bedrock-2023-05-31',
            },
            streaming=False,
            system_prompt_with_tools=SYSTEM_PROMPT,
        )

        # Prepare tools for Bedrock
        logger.info('Preparing tools for Bedrock')
        model = chat_model.bind_tools(tools)

        # Start conversation with Bedrock - include KB ID in the message
        kb_info = f'Use knowledge base ID: {kb_id} for any knowledge base queries.'
        enhanced_query = f'{kb_info}\n\nUser query: {query}'
        messages = [HumanMessage(content=enhanced_query)]

        logger.info('Sending initial query to Bedrock')
        response = await model.ainvoke(
            messages,
        )

        # Check if Bedrock requested a tool
        if hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info('Bedrock requested tool use')
            logger.info(f'Tool calls: {response.tool_calls}')

            for tool_call in response.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                tool_id = tool_call['id']

                logger.info(f'Tool requested: {tool_name} with args: {tool_args}')

                # Find the requested tool
                requested_tool = None
                for tool in tools:
                    if tool.name == tool_name:
                        requested_tool = tool
                        break

                if not requested_tool:
                    logger.warning(f'Requested tool {tool_name} not found')
                    continue

                # For query_knowledge_base tool, ensure we use the correct KB ID
                if tool_name == 'query_knowledge_base':
                    # Always override kb_id with the one from the request
                    tool_args['kb_id'] = kb_id

                # Execute the tool
                logger.info(f'Executing tool {tool_name}')
                tool_result = await requested_tool.ainvoke(tool_args)
                logger.debug(f'Tool result: {tool_result}')

                # Create a new conversation with the tool response - use the original query
                new_messages = [HumanMessage(content=enhanced_query)]
                new_messages.append(response)  # Add the original AI response with tool_calls
                new_messages.append(
                    ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_id,
                        name=tool_name,
                    )
                )

                # Get final response from Bedrock with tool results
                logger.info('Sending tool results back to Bedrock')
                final_response = await model.ainvoke(new_messages)
                response_content = str(final_response.content)

                return {'messages': [{'content': response_content}]}

        # If no tool was requested, return the direct response
        return {'messages': [{'content': response.content}]}

    except Exception as e:
        logger.error(f'Error in process_query: {str(e)}')
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f'Error processing query: {str(e)}')


# Define API endpoints
@app.post('/query', response_model=QueryResponse)
async def query(request: QueryRequest):
    """Process a query using the Bedrock KB."""
    logger.info(f'Received query request: {request.query}, KB ID: {request.kb_id}')
    try:
        result = await process_query(request.query, request.kb_id)
        logger.info('Query processed successfully')
        return result
    except Exception as e:
        logger.error(f'Error processing query: {str(e)}')
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/health')
def health_check():
    """Health check endpoint."""
    return {'status': 'healthy'}


@app.post('/kb', response_model=KnowledgeBaseResponse)
def add_knowledge_base(request: KnowledgeBaseRequest):
    """Add a new knowledge base ID."""
    # In a real implementation, this might validate the KB ID with AWS
    return {
        'message': f'Knowledge base {request.kb_id} added successfully',
        'kb_id': request.kb_id,
    }


@app.get('/kb')
def list_knowledge_bases():
    """List all knowledge bases (placeholder)."""
    # In a real implementation, this might fetch from a database
    return {'knowledge_bases': []}


# Run the FastAPI app with uvicorn
if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='127.0.0.1', port=8000)
