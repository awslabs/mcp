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

"""Register ServiceEvents data tools on the shared ServiceEvents MCP server."""

from .tools import (
    find_deployment,
    get_endpoints,
    get_function_details,
    get_health_overview,
    get_incident_details,
    get_incidents,
    list_functions,
    search_functions,
)


def register_tools(mcp) -> None:
    """Register all ServiceEvents data MCP tools onto a shared server."""
    mcp.tool(name='list_monitored_functions')(list_functions)
    mcp.tool(name='get_function_metrics')(get_function_details)
    mcp.tool(name='search_functions_by_name')(search_functions)
    mcp.tool(name='get_endpoint_performance')(get_endpoints)
    mcp.tool(name='get_recent_incidents')(get_incidents)
    mcp.tool(name='get_incident_root_cause')(get_incident_details)
    mcp.tool(name='get_service_health_overview')(get_health_overview)
    mcp.tool(name='find_deployment')(find_deployment)
