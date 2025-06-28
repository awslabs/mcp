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

"""Amazon OpenSearch Serverless tools for the MCP server."""

from awslabs.opensearch_mcp_server.constants import MCP_SERVER_VERSION
from awslabs.opensearch_mcp_server.generator import AWSToolGenerator
from mcp.server.fastmcp import FastMCP


def register_opensearchserverless_tools(mcp: FastMCP):
    """Register Amazon OpenSearch Serverless tools with the MCP server."""
    # List of supported operations
    supported_operations = [
        'batch_get_collection',
        'batch_get_effective_lifecycle_policy',
        'batch_get_lifecycle_policy',
        'batch_get_vpc_endpoint',
        'get_access_policy',
        'get_account_settings',
        'get_policies_stats',
        'get_security_config',
        'get_security_policy',
        'list_access_policies',
        'list_collections',
        'list_lifecycle_policies',
        'list_security_configs',
        'list_security_policies',
        'list_tags_for_resource',
        'list_vpc_endpoints',
    ]

    # Create the tool configuration dictionary
    tool_configuration = {}

    for operation in supported_operations:
        tool_configuration[operation] = {'supported': True}

    opensearchserverless_generator = AWSToolGenerator(
        service_name='opensearchserverless',
        service_display_name='Amazon OpenSearch Serverless',
        mcp=mcp,
        mcp_server_version=MCP_SERVER_VERSION,
        tool_configuration=tool_configuration,
        skip_param_documentation=True,
    )
    opensearchserverless_generator.generate()
