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

"""Main server module for Amazon OpenSearch MCP Server."""

from awslabs.opensearch_mcp_server.constants import MCP_SERVER_VERSION
from awslabs.opensearch_mcp_server.opensearch import register_opensearch_tools
from awslabs.opensearch_mcp_server.opensearchserverless import register_opensearchserverless_tools
from awslabs.opensearch_mcp_server.osis import register_osis_tools
from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    'awslabs.opensearch-mcp-server',
    instructions='Manage Amazon OpenSearch service domains, collection, ingestion pipelines via MCP server',
    dependencies=['pydantic', 'boto3'],
    version=MCP_SERVER_VERSION,
)


def main():
    """Run the MCP server with CLI argument support."""
    register_opensearch_tools(mcp)
    register_opensearchserverless_tools(mcp)
    register_osis_tools(mcp)

    mcp.run()


if __name__ == '__main__':
    main()
