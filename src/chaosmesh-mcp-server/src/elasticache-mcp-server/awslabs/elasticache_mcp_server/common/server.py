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

"""Common MCP server configuration."""

from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    'awslabs.elasticache-mcp-server',
    instructions="""AWS ElastiCache MCP Server provides tools for interacting with Amazon ElastiCache.
    These tools allow you to describe and manage serverless caches in your AWS account.
    You can use these capabilities to get information about cache configurations, endpoints, and more.""",
    dependencies=[
        'pydantic',
        'loguru',
        'boto3',
    ],
)
