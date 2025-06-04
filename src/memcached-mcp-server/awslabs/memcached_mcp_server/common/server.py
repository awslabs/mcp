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

"""Server initialization for Memcached MCP Server."""

from mcp.server.fastmcp import FastMCP


# Create MCP server instance
mcp = FastMCP(
    'awslabs.memcached-mcp-server',
    instructions='Instructions for using this memcached MCP server. This can be used by clients to improve the LLM'
    's understanding of available tools, resources, etc. It can be thought of like a '
    'hint'
    ' to the model. For example, this information MAY be added to the system prompt. Important to be clear, direct, and detailed.',
    dependencies=['pydantic', 'loguru', 'pymemcache', 'dotenv'],
)
