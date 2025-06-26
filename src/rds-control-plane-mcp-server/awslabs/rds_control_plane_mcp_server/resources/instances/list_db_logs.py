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

"""List DB Log File handler for the RDS Control Plane MCP Server."""

import json
from awslabs.rds_control_plane_mcp_server.common.config import get_pagination_config
from awslabs.rds_control_plane_mcp_server.common.constants import RESOURCE_PREFIX_DB_LOG_FILES
from awslabs.rds_control_plane_mcp_server.common.models import DBLogFileListModel, DBLogFileSummary
from awslabs.rds_control_plane_mcp_server.common.utils import (
    convert_datetime_to_string,
    handle_aws_error,
)
from datetime import datetime
from mypy_boto3_rds import RDSClient
from pydantic import Field
from typing import List


LIST_DB_LOG_FILES_RESOURCE_DESCRIPTION = """List all available log files for a specific Amazon RDS instance.

<use_case>
Use this resource to discover all available log files for a specific RDS database instance.
Log files provide detailed logs of database activities, helping you troubleshoot issues and monitor performance.
</use_case>

<important_notes>
1. The response provides information about log files generated for the instance
2. You must provide a valid DB instance identifier to retrieve log files
3. Log files are only available for instances with logs enabled
4. Log files are provided in chronological order with the most recent log files first
</important_notes>

## Response structure
Returns an array of log file objects, each containing:
- `log_file_identifier`: Unique identifier for the log file (string)
- `last_write_time`: Time when the log file was last written to (datetime)
- `size`: Size of the log file in bytes (integer)

<examples>
Example usage scenarios:
1. Log analysis:
   - List all available log files to identify periods of potential issues
   - Track log files generated during specific time periods of interest

2. Log troubleshooting:
   - Find specific log file identifiers for detailed log analysis
   - Monitor the status of recently generated log files
   - Identify long-running or failed log files that may need investigation
</examples>
"""


class ListDBLogsHandler:
    """Handler for RDS DB Log File listing operations in the RDS MCP Server.

    This class provides tools for discovering and retrieving information about availble
    RDS database log files in a specific DB Instance.
    """

    def __init__(self, mcp, rds_client: RDSClient):
        """Initialize the RDS DB Log File handler.

        Args:
            mcp: The MCP server instance
            rds_client: The AWS RDS client instance
        """
        self.mcp = mcp
        self.rds_client = rds_client

        # Register resources
        self.mcp.resource(
            uri='aws-rds://db-instance/{db_instance_identifier}/log',
            name='ListDBLogFiles',
            mime_type='application/json',
            description=LIST_DB_LOG_FILES_RESOURCE_DESCRIPTION,
        )(self.list_db_log_files)

    async def list_db_log_files(
        self,
        db_instance_identifier: str = Field(..., description='The identifier for the DB instance'),
    ) -> str:
        """List all non-empty log files for the database.

        Args:
            db_instance_identifier: The identifier of the DB instance.
            rds_client: An initialized RDS client.
            ctx: The FastMCP context object for request handling.

        Returns:
            DBLogFilesResponse: A model containing a list of DBLogFileOverview objects
                            representing non-empty log files.
            Dict[str, Any]: Error response if an exception occurs.

        Raises:
            ValueError: If input parameters are invalid or missing.
        """
        try:
            paginator = self.rds_client.get_paginator('describe_db_log_files')
            # Do not include empty database log files
            page_iterator = paginator.paginate(
                DBInstanceIdentifier=db_instance_identifier,
                FileSize=1,
                PaginationConfig=get_pagination_config(),
            )

            log_files: List[DBLogFileSummary] = []
            for response in page_iterator:
                for log_file in response.get('DescribeDBLogFiles', []):
                    # Convert AWS response to DBLogFileOverview objects
                    log_files.append(
                        DBLogFileSummary(
                            log_file_name=log_file.get('LogFileName', ''),
                            last_written=datetime.fromtimestamp(
                                log_file.get('LastWritten', 0) / 1000
                            ),
                            size=log_file.get('Size', 0),
                        )
                    )

            result = DBLogFileListModel(
                log_files=log_files,
                count=len(log_files),
                resource_uri=RESOURCE_PREFIX_DB_LOG_FILES.format(db_instance_identifier),
            )

            # Convert datetime objects to strings for JSON serialization
            result_dict = result.model_dump()
            serializable_dict = convert_datetime_to_string(result_dict)

            return json.dumps(serializable_dict, indent=2)

        except Exception as e:
            error_result = await handle_aws_error(
                f'list_db_log_files({db_instance_identifier})', e, None
            )
            return json.dumps(error_result, indent=2)
