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

"""Resource for listing availble RDS DB Log File."""

from ...common.connection import RDSConnectionManager
from ...common.decorator import handle_exceptions
from ...common.server import mcp
from ...context import Context
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List


LIST_DB_LOG_FILES_RESOURCE_DESCRIPTION = """List all available NON-EMPTY log files for a specific Amazon RDS instance.

<use_case>
Use this resource to discover all non-empty log files for a specific RDS database instance.
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


class DBLogFileSummary(BaseModel):
    """Database log file information.

    This model represents an Amazon RDS database log file with its metadata,
    including name, last modification time, and size.

    Attributes:
        log_file_name: The name of the log file in the database instance.
        last_written: A POSIX timestamp when the last log entry was written.
        size: Size of the log file in bytes.
    """

    log_file_name: str = Field(
        description='Name of the log file',
    )
    last_written: datetime = Field(
        description='A POSIX timestamp when the last log entry was written.'
    )
    size: int = Field(description='Size of the log file in bytes', ge=0)


class DBLogFileListModel(BaseModel):
    """DB cluster list model."""

    log_files: List[DBLogFileSummary] = Field(
        default_factory=list, description='List of DB log files'
    )
    count: int = Field(
        description='Total number of non-empty log files for the DB instance in Amazon RDS'
    )
    resource_uri: str = Field(description='The resource URI for the DB log files')


@mcp.resource(
    uri='aws-rds://db-instance/{db_instance_identifier}/log',
    name='ListDBLogFiles',
    mime_type='application/json',
    description=LIST_DB_LOG_FILES_RESOURCE_DESCRIPTION,
)
@handle_exceptions
async def list_db_log_files(
    db_instance_identifier: str = Field(..., description='The identifier for the DB instance'),
) -> DBLogFileListModel:
    """List all non-empty log files for the database.

    Args:
        db_instance_identifier: The identifier of the DB instance.

    Returns:
        JSON string containing a list of DBLogFileOverview objects representing non-empty log files.
    """
    rds_client = RDSConnectionManager.get_connection()

    paginator = rds_client.get_paginator('describe_db_log_files')
    # Do not include empty database log files
    page_iterator = paginator.paginate(
        DBInstanceIdentifier=db_instance_identifier,
        FileSize=1,
        PaginationConfig=Context.get_pagination_config(),
    )

    log_files: List[DBLogFileSummary] = []
    for response in page_iterator:
        for log_file in response.get('DescribeDBLogFiles', []):
            # Convert AWS response to DBLogFileOverview objects
            log_files.append(
                DBLogFileSummary(
                    log_file_name=log_file.get('LogFileName', ''),
                    last_written=datetime.fromtimestamp(log_file.get('LastWritten', 0) / 1000),
                    size=log_file.get('Size', 0),
                )
            )

    result = DBLogFileListModel(
        log_files=log_files,
        count=len(log_files),
        resource_uri='aws-rds://db-instance/{db_instance_identifier}/log',
    )

    return result
