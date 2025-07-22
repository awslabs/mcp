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
from ...common.connection import RDSConnectionManager
from ...common.constants import (
    SUCCESS_DELETED,
)
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.decorators.readonly_check import readonly_check
from ...common.decorators.require_confirmation import require_confirmation
from ...common.server import mcp
from ...common.utils import (
    format_rds_api_response,
)
from loguru import logger
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
@require_confirmation('DeleteDBInstance')
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
) -> Dict[str, Any]:
    """Delete an RDS database instance.

    Args:
        db_instance_identifier: The identifier for the DB instance
        skip_final_snapshot: Determines whether a final DB snapshot is created
        final_db_snapshot_identifier: The DB snapshot identifier if creating final snapshot
        confirmation_token: The confirmation token for the operation

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
