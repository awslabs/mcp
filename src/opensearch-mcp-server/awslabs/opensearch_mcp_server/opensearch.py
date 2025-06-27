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

"""Amazon OpenSearch Managed Service tools for the MCP server."""

from awslabs.opensearch_mcp_server.constants import MCP_SERVER_VERSION
from awslabs.opensearch_mcp_server.generator import AWSToolGenerator
from mcp.server.fastmcp import FastMCP


def register_opensearch_tools(mcp: FastMCP):
    """Register Amazon OpenSearch Managed Service tools with the MCP server."""
    # List of supported operations
    supported_operations = [
        'describe_domain',
        'describe_domain_auto_tunes',
        'describe_domain_change_progress',
        'describe_domain_config',
        'describe_domain_health',
        'describe_domain_nodes',
        'describe_domains',
        'describe_dry_run_progress',
        'describe_inbound_connections',
        'describe_instance_type_limits',
        'describe_outbound_connections',
        'describe_packages',
        'describe_reserved_instance_offerings',
        'describe_reserved_instances',
        'describe_vpc_endpoints',
        'get_application',
        'get_compatible_versions',
        'get_data_source',
        'get_direct_query_data_source',
        'get_domain_maintenance_status',
        'get_package_version_history',
        'get_upgrade_history',
        'get_upgrade_status',
        'list_applications',
        'list_data_sources',
        'list_direct_query_data_sources',
        'list_domain_maintenances',
        'list_domain_names',
        'list_domains_for_package',
        'list_instance_type_details',
        'list_packages_for_domain',
        'list_scheduled_actions',
        'list_tags',
        'list_versions',
        'list_vpc_endpoint_access',
        'list_vpc_endpoints',
        'list_vpc_endpoints_for_domain',
    ]

    # Create the tool configuration dictionary
    tool_configuration = {}

    for operation in supported_operations:
        tool_configuration[operation] = {'supported': True}

    opensearch_generator = AWSToolGenerator(
        service_name='opensearch',
        service_display_name='Amazon OpenSearch Service',
        mcp=mcp,
        mcp_server_version=MCP_SERVER_VERSION,
        tool_configuration=tool_configuration,
        skip_param_documentation=True,
    )
    opensearch_generator.generate()
