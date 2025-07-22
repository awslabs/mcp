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

from .constants import MCP_SERVER_VERSION
from mcp.server.fastmcp import FastMCP


"""Common MCP server configuration."""

SERVER_INSTRUCTIONS = """AWS RDS Control Plane MCP Server provides tools for interacting with Amazon RDS.
These tools allow you to monitor, analyze, and manage RDS database instances and clusters.
You can use these capabilities to get information about configurations, performance metrics, logs, and more."""

SERVER_DEPENDENCIES = ['pydantic', 'loguru', 'boto3', 'mypy-boto3-rds', 'mypy-boto3-cloudwatch']

mcp = FastMCP(
    'awslabs.rds-control-plane-mcp-server',
    version=MCP_SERVER_VERSION,
    instructions=SERVER_INSTRUCTIONS,
    dependencies=SERVER_DEPENDENCIES,
)
