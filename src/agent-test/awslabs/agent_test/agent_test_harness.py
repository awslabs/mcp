"""Agent testing harness for MCP tools.

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

from langchain_aws.chat_models import ChatBedrockConverse
from langchain_mcp_adapters.client import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import Dict, List, Optional


class AgentTestHarness:
    """A class for testing agents."""

    def __init__(
        self,
        mcp_args: List[str],
        mcp_env: Optional[Dict[str, str]],
        model_id: str = 'us.anthropic.claude-3-7-sonnet-20250219-v1:0',
        region_name: str = 'us-west-2',
        mcp_command: str = 'uvx',
    ):
        """Initialize the AgentTestHarness.

        Args:
            mcp_args: List of arguments to pass to the MCP server
            mcp_env: Optional environment variables to set for the MCP server
            model_id: Bedrock model ID to use for agent
            region_name: AWS region name for Bedrock
            mcp_command: Command to use for launching MCP server
        """
        self.model_id = model_id
        self.mcp_command = mcp_command
        self.mcp_args = mcp_args
        self.mcp_env = mcp_env
        self.region_name = region_name
        # Context manager resources
        self._mcp_client = None
        self._read_mcp = None
        self._write_mcp = None
        self._session = None
        self._agent = None

    def _get_server_parameters(self) -> StdioServerParameters:
        """Get a MCP server parameters."""
        return StdioServerParameters(
            command=self.mcp_command,
            args=self.mcp_args,
            env=self.mcp_env,
        )

    def _get_mcp_stdio_client(self):
        """Get a MCP stdio client."""
        return stdio_client(self._get_server_parameters())

    async def __aenter__(self):
        """Enter context manager."""
        self._mcp_client = self._get_mcp_stdio_client()
        self._read_mcp, self._write_mcp = await self._mcp_client.__aenter__()
        self._session = ClientSession(self._read_mcp, self._write_mcp)
        await self._session.__aenter__()
        await self._session.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and clean up resources."""
        if self._session is not None:
            await self._session.__aexit__(exc_type, exc_val, exc_tb)
            self._session = None

        if self._mcp_client is not None:
            await self._mcp_client.__aexit__(exc_type, exc_val, exc_tb)
            self._mcp_client = None

        self._agent = None

    async def get_agent(self):
        """Get an agent that can be used to test the model."""
        if self._session is None:
            raise RuntimeError('AgentTestHarness must be used as a context manager')

        if self._agent is None:
            tools = await load_mcp_tools(self._session)
            self._agent = create_react_agent(
                model=ChatBedrockConverse(model=self.model_id, region_name=self.region_name),
                tools=tools,
            )

        return self._agent
