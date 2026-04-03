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
"""MCP Test Client using the official MCP Python SDK."""

import logging
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class StdioMcpClient:
    """MCP client for testing servers over stdio transport using the official SDK."""

    def __init__(self, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        """Initialize the MCP test client."""
        self.command = command
        self.args = args
        self.env = env or {}
        self.server_params = StdioServerParameters(command=command, args=args, env=self.env)
        self.session: Optional[ClientSession] = None
        self._capabilities: Optional[Dict[str, Any]] = None

    async def connect(self) -> Dict[str, Any]:
        """Connect to the MCP server and initialize the connection."""
        try:
            # Create stdio client and session
            self.transport = stdio_client(self.server_params)
            self.read, self.write = await self.transport.__aenter__()

            self.session = ClientSession(self.read, self.write)
            await self.session.__aenter__()

            # Initialize the session
            init_result = await self.session.initialize()
            self._capabilities = (
                init_result.serverInfo.model_dump() if init_result.serverInfo else {}
            )

            logger.info('Successfully connected to MCP server')
            return self._capabilities

        except Exception as e:
            logger.error(f'Failed to connect to MCP server: {e}')
            await self.disconnect()
            raise

    async def disconnect(self):
        """Disconnect from the MCP server and cleanup resources."""
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)

            if hasattr(self, 'transport'):
                await self.transport.__aexit__(None, None, None)

        except Exception as e:
            logger.error(f'Error during disconnect: {e}')
        finally:
            self.session = None
            self._capabilities = None

    async def ping(self) -> bool:
        """Send a ping to the server to check if it's alive."""
        try:
            # MCP doesn't have a standard ping method, so we'll try to list tools
            # If it succeeds, the server is alive
            await self.session.list_tools()
            return True
        except Exception as e:
            logger.error(f'Ping failed: {e}')
            return False

    async def list_tools(self) -> List[types.Tool]:
        """List all available tools."""
        try:
            tools_response = await self.session.list_tools()
            return tools_response.tools

        except Exception as e:
            logger.error(f'Failed to list tools: {e}')
            return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> types.CallToolResult:
        """Call a specific tool with given arguments."""
        try:
            result = await self.session.call_tool(name, arguments)
            return result

        except Exception as e:
            logger.error(f'Failed to call tool {name}: {e}')
            raise

    async def list_resources(self) -> List[types.Resource]:
        """List all available resources."""
        try:
            resources_response = await self.session.list_resources()
            return resources_response.resources

        except Exception as e:
            logger.error(f'Failed to list resources: {e}')
            return []

    async def read_resource(self, uri: str) -> types.ReadResourceResult:
        """Read a specific resource."""
        try:
            result = await self.session.read_resource(uri)
            return result

        except Exception as e:
            logger.error(f'Failed to read resource {uri}: {e}')
            raise

    async def list_prompts(self) -> List[types.Prompt]:
        """List all available prompts."""
        try:
            prompts_response = await self.session.list_prompts()
            return prompts_response.prompts

        except Exception as e:
            logger.error(f'Failed to list prompts: {e}')
            return []

    async def get_prompt(self, name: str, arguments: Dict[str, Any]) -> types.GetPromptResult:
        """Get a specific prompt with given arguments."""
        try:
            result = await self.session.get_prompt(name, arguments)
            return result

        except Exception as e:
            logger.error(f'Failed to get prompt {name}: {e}')
            raise

    @property
    def capabilities(self) -> Optional[Dict[str, Any]]:
        """Get the server capabilities."""
        return self._capabilities


# Alias for backward compatibility
MCPTestClient = StdioMcpClient
