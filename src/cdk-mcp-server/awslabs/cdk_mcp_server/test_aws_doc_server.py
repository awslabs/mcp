#!/usr/bin/env python3
"""
Test script to demonstrate calling AWS Documentation MCP Server using FastMCP.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_aws_doc_mcp_server():
    """Test calling AWS Documentation MCP Server using FastMCP."""
    try:
        # Import FastMCP
        from mcp.server.fastmcp import FastMCP
        # logger.info("Successfully imported FastMCP")
        
        # Define the server name
        server_name = "awslabs.aws-documentation-mcp-server"
        
        # Create a FastMCP client
        mcp = FastMCP(
            # name=server_name
        )
        
        # # Step 1: Try to list tools from the AWS Documentation MCP Server
        # logger.info(f"Attempting to list tools from {server_name}...")
        # try:
        #     # First approach: Try to use list_tools with a server parameter
        #     tools = await mcp.list_tools()
        #     logger.info(f"Tools from {server_name}: {json.dumps(tools, indent=2)}")
        # except Exception as e:
        #     logger.warning(f"Could not list tools with server parameter: {str(e)}")
        #     logger.info("Trying alternative approaches...")
            
        #     # Second approach: Try to use call_tool to call a special list_tools method
        #     try:
        #         tools = await mcp.call_tool(
        #             name="list_tools"
        #         )
        #         logger.info(f"Tools from {server_name}: {json.dumps(tools, indent=2)}")
        #     except Exception as e:
        #         logger.warning(f"Could not call list_tools tool: {str(e)}")
                
        #         # Third approach: Try to start the server and then list tools
        #         logger.info("Trying to start the server and then list tools...")
        #         # This is a placeholder - we'd need to implement server starting logic
        #         tools = ["read_documentation", "search_documentation", "recommend"]  # Assumed tools
        
        # Step 2: Try to call the read_documentation tool
        logger.info(f"Attempting to call read_documentation tool on {server_name}...")
        url = "https://docs.aws.amazon.com/cdk/api/v1/docs/aws-lambda-readme.html#layers"
        
        try:
            # First approach: Try to use call_tool with a server parameter
            result = await mcp.call_tool(
                name="read_documentation", 
                arguments={"url": url, "max_length": 5000},
            )
            logger.info(f"Successfully called read_documentation on {server_name}")
            logger.info(f"Result snippet: {result.get('text', '')[:200]}...")
        except Exception as e:
            logger.warning(f"Could not call read_documentation with server parameter: {str(e)}")
            
            # # Second approach: Try to use a different method signature
            # try:
            #     result = await mcp.call_tool(
            #         name="read_documentation", 
            #         arguments={"url": url, "max_length": 5000},
            #     )
            #     logger.info(f"Successfully called read_documentation on {server_name}")
            #     logger.info(f"Result snippet: {result.get('text', '')[:200]}...")
            # except Exception as e:
            #     logger.warning(f"Could not call read_documentation with server_name parameter: {str(e)}")
                
                # # Third approach: Try to use a fully qualified tool name
                # try:
                #     result = await mcp.call_tool(
                #         f"{server_name}.read_documentation", 
                #         {"url": url, "max_length": 5000}
                #     )
                #     logger.info(f"Successfully called read_documentation on {server_name}")
                #     logger.info(f"Result snippet: {result.get('text', '')[:200]}...")
                # except Exception as e:
                #     logger.warning(f"Could not call read_documentation with fully qualified name: {str(e)}")
                #     logger.error("All approaches failed to call read_documentation")
        
        # # Step 3: Try to access a resource
        # logger.info(f"Attempting to list resources from {server_name}...")
        # try:
        #     resources = await mcp.list_resources(server=server_name)
        #     logger.info(f"Resources from {server_name}: {json.dumps(resources, indent=2)}")
        # except Exception as e:
        #     logger.warning(f"Could not list resources: {str(e)}")
        
        return {
            "status": "exploration_complete",
            "message": "Check the logs for detailed results"
        }
        
    except Exception as e:
        logger.error(f"Error exploring FastMCP: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_aws_doc_mcp_server())
    print(json.dumps(result, indent=2))