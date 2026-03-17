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

"""awslabs cross-account CloudWatch MCP Server implementation."""

from datetime import datetime
from awslabs.cross_account_cloudwatch_mcp_server.tools import CrossAccountCloudWatchTools
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Annotated


mcp = FastMCP(
    'awslabs.cross-account-cloudwatch-mcp-server',
    instructions=(
        'Use this MCP server to inspect configured CloudWatch targets and query CloudWatch '
        'Logs across multiple AWS accounts by assuming a standard IAM role via STS '
        'AssumeRole. Supports listing configured targets and running CloudWatch Logs '
        'Insights queries in any target account, including automatically partitioned '
        'parallel queries when a result window reaches the CloudWatch row limit.'
    ),
    dependencies=[
        'pydantic',
        'loguru',
    ],
)

try:
    tools = CrossAccountCloudWatchTools()

    @mcp.tool()
    async def list_cw_targets(ctx: Context):
        """List configured CloudWatch targets available for cross-account queries."""
        return await tools.list_cw_targets(ctx)

    @mcp.tool()
    async def query_logs(
        ctx: Context,
        account_id: Annotated[
            str,
            Field(description='12-digit AWS account ID to query.', pattern=r'^\d{12}$'),
        ],
        log_group: Annotated[
            str,
            Field(description='CloudWatch log group name to query.'),
        ],
        query_string: Annotated[
            str,
            Field(
                description='CloudWatch Logs Insights query string. Include a limit to control response size.'
            ),
        ],
        start_time: Annotated[
            datetime,
            Field(
                description='Start time for the query window. Timezone-aware values are converted to UTC; naive values are treated as UTC.'
            ),
        ],
        end_time: Annotated[
            datetime,
            Field(
                description='End time for the query window. Timezone-aware values are converted to UTC; naive values are treated as UTC.'
            ),
        ],
        role_name: Annotated[
            str,
            Field(description='IAM role name to assume in the target account.'),
        ] = 'DevAccessReadOnly',
        region: Annotated[
            str,
            Field(description='AWS region. Defaults to us-west-2.'),
        ] = 'us-west-2',
        max_timeout: Annotated[
            int,
            Field(description='Max seconds to wait for query completion. Defaults to 30.', gt=0),
        ] = 30,
    ):
        """Query CloudWatch Logs with automatic UTC normalization and parallel partitioning."""
        return await tools.query_logs(
            ctx=ctx,
            account_id=account_id,
            log_group=log_group,
            query_string=query_string,
            start_time=start_time,
            end_time=end_time,
            role_name=role_name,
            region=region,
            max_timeout=max_timeout,
        )

    logger.info('Cross-account CloudWatch tools registered successfully')
except Exception as e:
    logger.error(f'Error initializing cross-account CloudWatch tools: {e}')
    raise


def main():
    """Run the MCP server."""
    mcp.run()
    logger.info('Cross-account CloudWatch MCP server started')


if __name__ == '__main__':
    main()
