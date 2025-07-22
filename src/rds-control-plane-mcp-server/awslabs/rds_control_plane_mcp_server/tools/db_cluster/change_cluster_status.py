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

"""Tool to manage the status of an Amazon RDS database cluster."""

import asyncio
from ...common.connection import RDSConnectionManager
from ...common.constants import (
    SUCCESS_REBOOTED,
    SUCCESS_STARTED,
    SUCCESS_STOPPED,
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


CHANGE_CLUSTER_STATUS_TOOL_DESCRIPTION = """Manage the status of an RDS database cluster.

This tool changes the operational status of an Amazon RDS database cluster, allowing you to start, stop, or reboot a cluster.

<warning>
These operations affect database availability and billing. Stopping makes the database unavailable, starting resumes full charges, and rebooting causes a brief interruption. A confirmation token is required.
</warning>
"""


@mcp.tool(
    name='ChangeDBClusterStatus',
    description=CHANGE_CLUSTER_STATUS_TOOL_DESCRIPTION,
)
@handle_exceptions
@readonly_check
@require_confirmation('ChangeDBClusterStatus')
async def change_cluster_status(
    db_cluster_identifier: Annotated[str, Field(description='The identifier for the DB cluster')],
    action: Annotated[str, Field(description='Action to perform: "start", "stop", or "reboot"')],
    confirmation_token: Annotated[
        Optional[str], Field(description='Confirmation token for destructive operations')
    ] = None,
) -> Dict[str, Any]:
    """Change the status of an RDS database cluster.

    Args:
        db_cluster_identifier: The identifier for the DB cluster
        action: Action to perform: "start", "stop", or "reboot"
        confirmation_token: Confirmation token for destructive operations

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    # Validate action
    action = action.lower()
    if action not in ['start', 'stop', 'reboot']:
        return {'error': f'Invalid action: {action}. Must be one of: start, stop, reboot'}

    # AWS API parameters
    aws_params = {
        'DBClusterIdentifier': db_cluster_identifier,
    }

    # Execute the appropriate action
    if action == 'start':
        logger.info(f'Starting DB cluster {db_cluster_identifier}')
        response = await asyncio.to_thread(rds_client.start_db_cluster, **aws_params)
        success_message = SUCCESS_STARTED.format(f'DB cluster {db_cluster_identifier}')
    elif action == 'stop':
        logger.info(f'Stopping DB cluster {db_cluster_identifier}')
        response = await asyncio.to_thread(rds_client.stop_db_cluster, **aws_params)
        success_message = SUCCESS_STOPPED.format(f'DB cluster {db_cluster_identifier}')
    else:  # reboot
        logger.info(f'Rebooting DB cluster {db_cluster_identifier}')
        response = await asyncio.to_thread(rds_client.reboot_db_cluster, **aws_params)
        success_message = SUCCESS_REBOOTED.format(f'DB cluster {db_cluster_identifier}')

    logger.success(success_message)

    result = format_rds_api_response(response)
    result['message'] = success_message

    return result
