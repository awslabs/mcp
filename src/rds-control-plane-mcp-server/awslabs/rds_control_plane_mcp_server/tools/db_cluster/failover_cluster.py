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

"""Tool to force a failover for an Amazon RDS database cluster."""

import asyncio
from ...common.connection import RDSConnectionManager
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


SUCCESS_FAILED_OVER = '{} has been failed over successfully.'


FAILOVER_CLUSTER_TOOL_DESCRIPTION = """Force a failover for an RDS database cluster.

This tool forces a failover of an Amazon RDS Multi-AZ DB cluster, promoting a read replica to become the primary instance. This can be used for disaster recovery testing, to move the primary to a different availability zone, or to recover from issues with the current primary instance.

<warning>
Failover causes a momentary interruption in database availability and any in-flight transactions that haven't been committed may be lost. This operation requires explicit confirmation.
</warning>
"""


@mcp.tool(
    name='FailoverDBCluster',
    description=FAILOVER_CLUSTER_TOOL_DESCRIPTION,
)
@handle_exceptions
@readonly_check
@require_confirmation('FailoverDBCluster')
async def failover_db_cluster(
    db_cluster_identifier: Annotated[str, Field(description='The identifier for the DB cluster')],
    target_db_instance_identifier: Annotated[
        Optional[str],
        Field(description='The name of the instance to promote to the primary instance'),
    ] = None,
    confirmation_token: Annotated[
        Optional[str], Field(description='Confirmation token for destructive operation')
    ] = None,
) -> Dict[str, Any]:
    """Force a failover for an RDS database cluster.

    Args:
        db_cluster_identifier: The identifier for the DB cluster
        target_db_instance_identifier: The name of the instance to promote to the primary instance
        confirmation_token: Confirmation token for destructive operation

    Returns:
        Dict[str, Any]: The response from the AWS API
    """
    # Get RDS client
    rds_client = RDSConnectionManager.get_connection()

    aws_params = {
        'DBClusterIdentifier': db_cluster_identifier,
    }

    if target_db_instance_identifier:
        aws_params['TargetDBInstanceIdentifier'] = target_db_instance_identifier

    logger.info(f'Initiating failover for DB cluster {db_cluster_identifier}')
    response = await asyncio.to_thread(rds_client.failover_db_cluster, **aws_params)
    logger.success(f'Successfully initiated failover for DB cluster {db_cluster_identifier}')

    result = format_rds_api_response(response)
    result['message'] = SUCCESS_FAILED_OVER.format(f'DB cluster {db_cluster_identifier}')

    return result
