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

"""Amazon OpenSearch Ingestion Service tools for the MCP server."""

from awslabs.opensearch_mcp_server.constants import MCP_SERVER_VERSION
from awslabs.opensearch_mcp_server.generator import AWSToolGenerator
from mcp.server.fastmcp import FastMCP


def register_osis_tools(mcp: FastMCP):
    """Register Amazon OpenSearch Ingestion Service tools with the MCP server."""
    # List of supported operations
    supported_operations = [
        'get_pipeline',
        'get_pipeline_blueprint',
        'get_pipeline_change_progress',
        'list_pipeline_blueprints',
        'list_pipelines',
        'list_tags_for_resource',
        'validate_pipeline',
    ]

    # Create the tool configuration dictionary
    tool_configuration = {}

    for operation in supported_operations:
        tool_configuration[operation] = {'supported': True}

    osis_generator = AWSToolGenerator(
        service_name='osis',
        service_display_name='Amazon OpenSearch Ingestion Service',
        mcp=mcp,
        mcp_server_version=MCP_SERVER_VERSION,
        tool_configuration=tool_configuration,
        skip_param_documentation=True,
    )
    osis_generator.generate()
