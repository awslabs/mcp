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

"""Tool to delete an Amazon RDS database instance."""

import asyncio
from ...common.confirmation import readonly_check, require_confirmation
from ...common.connection import RDSConnectionManager
from ...common.exceptions import handle_exceptions
from ...common.server import mcp
from ...common.utils import (
    format_rds_api_response,
)
from ...constants import (
    SUCCESS_DELETED,
)
from loguru import logger
from mcp.server.fastmcp import Context as FastMCPContext
from pydantic import Field
from typing import Any, Dict, Optional
from typing_extensions import Annotated


DELETE_INSTANCE_TOOL_DESCRIPTION = """Delete an Amazon RDS database instance.

This tool deletes an RDS database instance. By default, a final snapshot will be created
unless explicitly disabled. This operation cannot be undone.

<warning>
This is a destructive operation that permanently deletes the database instance and all its data.
Without a final snapshot, all data will be permanently lost.
</warning>
"""


@mcp.tool(
    name='DeleteDBInstance',
    description=DELETE_INSTANCE_TOOL_DESCRIPTION,
)
@handle_exceptions
@readonly_check
@require_confirmation('delete_db_instance')
async def delete_db_instance(
    db_instance_identifier: Annotated[
        str, Field(description='The identifier for the DB instance')
    ],
    skip_final_snapshot: Annotated[
        bool,
        Field(
            description='Determines whether a final DB snapshot is created before the DB instance is deleted'
        ),
    ] = False,
    final_db_snapshot_identifier: Annotated[
        Optional[str],
        Field(
            description='The DB snapshot identifier of the new DB snapshot created when SkipFinalSnapshot is false'
        ),
    ] = None,
    confirmation_token: Annotated[
        Optional[str], Field(description='The confirmation token for the operation')
    ] = None,
    ctx: Optional[FastMCPContext] = None,
) -> Dict[str, Any]:
    """Delete an RDS database instance.

    Args:
        db_instance_identifier: The identifier for the DB instance
        skip_final_snapshot: Determines whether a final DB snapshot is created
        final_db_snapshot_identifier: The DB snapshot identifier if creating final snapshot
        confirmation_token: The confirmation token for the operation
        ctx: MCP context for logging and state management

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    # AWS API parameters
    aws_params = {
        'DBInstanceIdentifier': db_instance_identifier,
        'SkipFinalSnapshot': skip_final_snapshot,
    }

    if not skip_final_snapshot and final_db_snapshot_identifier:
        aws_params['FinalDBSnapshotIdentifier'] = final_db_snapshot_identifier

    logger.info(f'Deleting DB instance {db_instance_identifier}')
    response = await asyncio.to_thread(rds_client.delete_db_instance, **aws_params)
    logger.success(f'Successfully initiated deletion of DB instance {db_instance_identifier}')

    result = format_rds_api_response(response)
    result['message'] = SUCCESS_DELETED.format(f'DB instance {db_instance_identifier}')

    return result
