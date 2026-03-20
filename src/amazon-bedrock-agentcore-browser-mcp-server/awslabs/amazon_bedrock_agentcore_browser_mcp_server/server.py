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

"""Amazon Bedrock AgentCore Browser MCP Server."""

import sys

# Import tool functions
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.tools import (
    browsers,
    live_view,
    profiles,
    sessions,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP


APP_NAME = 'awslabs.amazon-bedrock-agentcore-browser-mcp-server'

mcp = FastMCP(
    APP_NAME,
    instructions="""
# Amazon Bedrock AgentCore Browser MCP Server

Manages ephemeral browser sessions on Amazon Bedrock AgentCore Browser.
Use this server to create isolated browser instances for web interaction,
get connection credentials (WebSocket endpoints), and manage session lifecycle.

## Tool Selection Guide

### Starting a workflow:
1. Use `list_browsers` to discover available browser tool IDs (system or VPC-bound custom)
2. Use `start_browser_session` to create an ephemeral browser session
3. Use the returned `automation_endpoint` (WebSocket URL) with Playwright or CDP to control the browser
4. Use `open_live_view` to get a URL for watching the browser session in real-time

### During a workflow:
- Use `get_browser_session` to check session status and get stream endpoints
- Use `list_browser_sessions` to see all active sessions

### Finishing a workflow:
- Use `save_browser_session_profile` to persist cookies/storage for reuse in future sessions
- Use `stop_browser_session` to terminate the session and release resources

### Browser identifiers:
- Default: "aws.browser.v1" (AWS-managed, public network)
- Custom browsers (VPC-bound) have unique IDs — use `list_browsers` to discover them

## Tips
- Sessions auto-terminate after the configured timeout (default: 15 minutes, max: 8 hours)
- Always stop sessions when done to avoid unnecessary costs
- Use profiles to maintain authentication state across sessions
""",
)

# Register session lifecycle tools
mcp.tool()(sessions.start_browser_session)
mcp.tool()(sessions.get_browser_session)
mcp.tool()(sessions.list_browser_sessions)
mcp.tool()(sessions.stop_browser_session)

# Register profile tool
mcp.tool()(profiles.save_browser_session_profile)

# Register browser discovery tools
mcp.tool()(browsers.list_browsers)
mcp.tool()(browsers.get_browser)

# Register live view tool
mcp.tool()(live_view.open_live_view)


def main() -> None:
    """Main entry point for the AgentCore Browser MCP server."""
    logger.remove()
    logger.add(sys.stderr, level='WARNING')
    mcp.run()


if __name__ == '__main__':
    main()
