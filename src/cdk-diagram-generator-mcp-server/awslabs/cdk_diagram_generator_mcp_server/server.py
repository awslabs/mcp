#!/usr/bin/env python3
"""CDK Diagram Generator MCP Server.

This server provides tools to generate architectural diagrams from AWS CDK code.
"""

import logging
import os
import sys
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import StdioServerTransport
from mcp.types import (
    CallToolRequestSchema,
    ErrorCode,
    ListToolsRequestSchema,
    McpError,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr,
)
logger = logging.getLogger('cdk-diagram-generator-mcp-server')


class CDKDiagramGeneratorServer:
    """CDK Diagram Generator MCP Server."""

    def __init__(self) -> None:
        """Initialize the server."""
        self.server = Server(
            {
                'name': 'cdk-diagram-generator-mcp-server',
                'version': '0.0.1',
            },
            {
                'capabilities': {
                    'tools': {},
                },
            },
        )

        # Set up request handlers
        self.setup_tool_handlers()

        # Set up error handler
        self.server.onerror = self._on_error

    def setup_tool_handlers(self) -> None:
        """Set up tool request handlers."""
        self.server.set_request_handler(ListToolsRequestSchema, self._handle_list_tools)
        self.server.set_request_handler(CallToolRequestSchema, self._handle_call_tool)

    async def _handle_list_tools(self, _: Any) -> Dict[str, List[Dict[str, Any]]]:
        """Handle list_tools request."""
        return {
            'tools': [
                {
                    'name': 'generate_diagram_from_code',
                    'description': 'Generate a diagram from CDK code',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'code': {
                                'type': 'string',
                                'description': 'CDK code to generate a diagram from',
                            },
                            'language': {
                                'type': 'string',
                                'description': 'Language of the CDK code (typescript or python)',
                                'enum': ['typescript', 'python'],
                            },
                        },
                        'required': ['code', 'language'],
                    },
                },
                {
                    'name': 'generate_diagram_from_directory',
                    'description': 'Generate a diagram from a directory containing CDK code',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'directory': {
                                'type': 'string',
                                'description': 'Directory containing CDK code',
                            },
                            'language': {
                                'type': 'string',
                                'description': 'Language of the CDK code (typescript or python)',
                                'enum': ['typescript', 'python'],
                            },
                        },
                        'required': ['directory', 'language'],
                    },
                },
            ],
        }

    async def _handle_call_tool(self, request: Any) -> Dict[str, Any]:
        """Handle call_tool request."""
        tool_name = request.params.name
        args = request.params.arguments

        if tool_name == 'generate_diagram_from_code':
            return await self._generate_diagram_from_code(args)
        elif tool_name == 'generate_diagram_from_directory':
            return await self._generate_diagram_from_directory(args)
        else:
            raise McpError(ErrorCode.MethodNotFound, f'Unknown tool: {tool_name}')

    async def _generate_diagram_from_code(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a diagram from CDK code."""
        # This is a wrapper around the TypeScript implementation
        # In a real implementation, this would call the TypeScript code
        return {
            'content': [
                {
                    'type': 'text',
                    'text': 'Diagram generated successfully. This is a placeholder for the actual diagram.',
                },
            ],
        }

    async def _generate_diagram_from_directory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a diagram from a directory containing CDK code."""
        # This is a wrapper around the TypeScript implementation
        # In a real implementation, this would call the TypeScript code
        return {
            'content': [
                {
                    'type': 'text',
                    'text': 'Diagram generated successfully. This is a placeholder for the actual diagram.',
                },
            ],
        }

    def _on_error(self, error: Exception) -> None:
        """Handle errors."""
        logger.error('Error: %s', error)

    async def run(self) -> None:
        """Run the server."""
        transport = StdioServerTransport()
        await self.server.connect(transport)
        logger.info('CDK Diagram Generator MCP server running on stdio')


def main() -> None:
    """Run the server."""
    import asyncio

    server = CDKDiagramGeneratorServer()
    asyncio.run(server.run())


if __name__ == '__main__':
    main()
