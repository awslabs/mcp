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

"""Tool to manage the status of an Amazon RDS database instance."""

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


CHANGE_INSTANCE_STATUS_TOOL_DESCRIPTION = """Manage the status of an Amazon RDS database instance.

This tool allows you to change the status of an RDS database instance:

- **Start**: Starts a stopped instance, making it available for connections
- **Stop**: Stops a running instance, making it unavailable until started again
- **Reboot**: Reboots a running instance, causing a brief interruption in availability

<warning>
These operations affect the availability of your database:
- Starting a stopped instance will resume billing charges
- Stopping an instance makes it unavailable until it's started again
- Rebooting an instance causes a brief service interruption
</warning>
"""


@mcp.tool(
    name='ChangeDBInstanceStatus',
    description=CHANGE_INSTANCE_STATUS_TOOL_DESCRIPTION,
)
@handle_exceptions
@readonly_check
@require_confirmation('ChangeDBInstanceStatus')
async def change_instance_status(
    db_instance_identifier: Annotated[
        str, Field(description='The identifier for the DB instance')
    ],
    action: Annotated[str, Field(description='Action to perform: "start", "stop", or "reboot"')],
    force_failover: Annotated[
        Optional[bool],
        Field(description='When rebooting, whether to force a failover to another AZ'),
    ] = False,
    confirmation_token: Annotated[
        Optional[str], Field(description='Confirmation token for destructive operations')
    ] = None,
) -> Dict[str, Any]:
    """Change the status of an RDS database instance.

    Args:
        db_instance_identifier: The identifier for the DB instance
        action: Action to perform: "start", "stop", or "reboot"
        force_failover: When rebooting, whether to force a failover to another AZ
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
    aws_params: Dict[str, Any] = {
        'DBInstanceIdentifier': db_instance_identifier,
    }

    # Execute the appropriate action
    if action == 'start':
        logger.info(f'Starting DB instance {db_instance_identifier}')
        response = await asyncio.to_thread(rds_client.start_db_instance, **aws_params)
        success_message = SUCCESS_STARTED.format(f'DB instance {db_instance_identifier}')
    elif action == 'stop':
        logger.info(f'Stopping DB instance {db_instance_identifier}')
        response = await asyncio.to_thread(rds_client.stop_db_instance, **aws_params)
        success_message = SUCCESS_STOPPED.format(f'DB instance {db_instance_identifier}')
    else:  # reboot
        if force_failover is not None:
            aws_params['ForceFailover'] = force_failover
        logger.info(f'Rebooting DB instance {db_instance_identifier}')
        response = await asyncio.to_thread(rds_client.reboot_db_instance, **aws_params)
        success_message = SUCCESS_REBOOTED.format(f'DB instance {db_instance_identifier}')

    logger.success(success_message)

    result = format_rds_api_response(response)
    result['message'] = success_message

    return result
