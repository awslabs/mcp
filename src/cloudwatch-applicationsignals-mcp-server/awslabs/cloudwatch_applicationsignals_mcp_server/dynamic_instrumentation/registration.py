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
)
from mcp.types import ToolAnnotations


def register_tools(mcp) -> None:
    """Register all dynamic instrumentation MCP tools onto a shared server.

    Tools carry MCP annotations so clients can distinguish read-only queries
    from state-changing operations (and warn before destructive bulk deletes).
    Every tool sets ``openWorldHint=True`` because each one calls the AWS API.
    """
    # State-changing: creates a new instrumentation configuration.
    mcp.tool(
        annotations=ToolAnnotations(
            title='Create Instrumentation',
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=True,
        )
    )(create_instrumentation)

    # Read-only queries.
    mcp.tool(
        annotations=ToolAnnotations(
            title='List Instrumentations', readOnlyHint=True, openWorldHint=True
        )
    )(list_instrumentations)
    mcp.tool(
        annotations=ToolAnnotations(
            title='Get Instrumentation', readOnlyHint=True, openWorldHint=True
        )
    )(get_instrumentation)

    # Destructive: deletes are idempotent (deleting an absent config is a no-op).
    mcp.tool(
        annotations=ToolAnnotations(
            title='Delete Instrumentation',
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=True,
        )
    )(delete_instrumentation)
    mcp.tool(
        annotations=ToolAnnotations(
            title='Batch Delete Instrumentations by Scope',
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=True,
        )
    )(batch_delete_instrumentations_by_scope)
    mcp.tool(
        annotations=ToolAnnotations(
            title='Batch Delete Instrumentations by ARNs',
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=True,
        )
    )(batch_delete_instrumentations_by_arns)

    # Read-only status queries.
    mcp.tool(
        annotations=ToolAnnotations(
            title='Get Instrumentation Configuration Status',
            readOnlyHint=True,
            openWorldHint=True,
        )
    )(get_instrumentation_configuration_status)
    mcp.tool(
        annotations=ToolAnnotations(
            title='Check Instrumentation Status', readOnlyHint=True, openWorldHint=True
        )
    )(check_instrumentation_status)

    # Read-only snapshot analysis.
    mcp.tool(
        annotations=ToolAnnotations(
            title='Search Snapshots for Status Event',
            readOnlyHint=True,
            openWorldHint=True,
        )
    )(search_snapshots_for_status_event)
    mcp.tool(
        annotations=ToolAnnotations(
            title='Get Sample Snapshot for Breakpoint',
            readOnlyHint=True,
            openWorldHint=True,
        )
    )(get_sample_snapshot_for_breakpoint)
