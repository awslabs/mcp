"""Test helpers for handling both string results and ToolError exceptions."""

from awslabs.amazon_bedrock_agentcore_mcp_server.utils import MCPtoolError
from mcp.server.fastmcp.exceptions import ToolError


class SmartTestHelper:
    """Helper class for tests that need to handle both old string patterns and new exception patterns."""

    def _extract_result(self, mcp_result):
        """Extract result string from MCP call_tool return value."""
        if isinstance(mcp_result, tuple) and len(mcp_result) >= 2:
            result_content = mcp_result[1]
            if isinstance(result_content, dict):
                return result_content.get('result', str(mcp_result))
            elif hasattr(result_content, 'content'):
                return str(result_content.content)
            return str(result_content)
        elif isinstance(mcp_result, list):
            # Handle list of TextContent objects
            if len(mcp_result) > 0 and hasattr(mcp_result[0], 'text'):
                return mcp_result[0].text
            elif len(mcp_result) > 0 and hasattr(mcp_result[0], 'content'):
                return str(mcp_result[0].content)
            return str(mcp_result)
        elif hasattr(mcp_result, 'content') and not isinstance(mcp_result, tuple):
            return str(mcp_result.content)
        return str(mcp_result)

    async def call_tool_and_extract(self, mcp, tool_name, params):
        """Smart helper that handles both string results and ToolError exceptions."""
        try:
            result_tuple = await mcp.call_tool(tool_name, params)
            return self._extract_result(result_tuple)
        except (ToolError, MCPtoolError, OSError) as e:
            # Extract the error message from any exception type for assertion compatibility
            return str(e)
