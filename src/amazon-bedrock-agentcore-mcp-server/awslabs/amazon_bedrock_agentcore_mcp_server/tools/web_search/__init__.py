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

"""Web Search tools sub-package for the unified AgentCore MCP server.

Provides 1 tool via the Amazon Bedrock AgentCore Web Search API:
- web_search: billable, read-only search of the web (InvokeWebSearch)
"""

from .search import web_search
from mcp.types import ToolAnnotations


def register_web_search_tools(mcp):
    """Register the web search tool with the MCP server."""
    mcp.tool(
        name='web_search',
        annotations=ToolAnnotations(title='Web search', read_only_hint=True, open_world_hint=True),
    )(web_search)
