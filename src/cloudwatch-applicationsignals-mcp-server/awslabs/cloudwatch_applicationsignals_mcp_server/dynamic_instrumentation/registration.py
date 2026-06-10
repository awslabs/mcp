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
"""Register dynamic instrumentation tools on the shared Application Signals MCP server."""

from .crud_tools import (
    batch_delete_instrumentations_by_arns,
    batch_delete_instrumentations_by_scope,
    create_instrumentation,
    delete_instrumentation,
    get_instrumentation,
    list_instrumentations,
)
from .snapshot_tools import get_sample_snapshot_for_breakpoint, search_snapshots_for_status_event
from .status_tools import (
    check_instrumentation_status,
    get_instrumentation_configuration_status,
    report_instrumentation_configuration_status,
)


def register_tools(mcp) -> None:
    """Register all dynamic instrumentation MCP tools onto a shared server."""
    mcp.tool()(create_instrumentation)
    mcp.tool()(list_instrumentations)
    mcp.tool()(get_instrumentation)
    mcp.tool()(delete_instrumentation)
    mcp.tool()(batch_delete_instrumentations_by_scope)
    mcp.tool()(batch_delete_instrumentations_by_arns)

    mcp.tool()(get_instrumentation_configuration_status)
    mcp.tool()(check_instrumentation_status)
    mcp.tool()(report_instrumentation_configuration_status)

    mcp.tool()(search_snapshots_for_status_event)
    mcp.tool()(get_sample_snapshot_for_breakpoint)
