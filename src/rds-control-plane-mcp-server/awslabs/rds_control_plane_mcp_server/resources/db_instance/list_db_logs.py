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
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.server import mcp
from ...common.utils import handle_paginated_aws_api_call
from datetime import datetime
from mypy_boto3_rds.type_defs import DescribeDBLogFilesResponseTypeDef
from pydantic import BaseModel, Field
from typing import List


LIST_DB_LOG_FILES_RESOURCE_DESCRIPTION = """List all available NON-EMPTY log files for a specific Amazon RDS instance.

This resource retrieves information about non-empty log files for a specific RDS database instance, which provide detailed logs of database activities for troubleshooting issues and monitoring performance.
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

    @classmethod
    def from_DescribeDBLogFilesDetailsTypeDef(
        cls, log_file: DescribeDBLogFilesResponseTypeDef
    ) -> 'DBLogFileSummary':
        """Convert AWS RDS log file details to DBLogFileSummary model.

        Args:
            log_file: Response dictionary containing log file details from RDS API
                    including LogFileName, LastWritten timestamp and Size

        Returns:
            DBLogFileSummary: Model instance containing the log file information
        """
        return cls(
            log_file_name=log_file.get('LogFileName', ''),
            last_written=datetime.fromtimestamp(log_file.get('LastWritten', 0) / 1000),
            size=log_file.get('Size', 0),
        )


class DBLogFileList(BaseModel):
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
) -> DBLogFileList:
    """List all non-empty log files for the database.

    Args:
        db_instance_identifier: The identifier of the DB instance.

    Returns:
        DBLogFileList: A model containing a list of DBLogFileSummary objects
    """
    rds_client = RDSConnectionManager.get_connection()

    params = {
        'DBInstanceIdentifier': db_instance_identifier,
        'FileSize': 1,
    }

    log_files = handle_paginated_aws_api_call(
        client=rds_client,
        paginator_name='describe_db_log_files',
        operation_parameters=params,
        format_function=DBLogFileSummary.from_DescribeDBLogFilesDetailsTypeDef,
        result_key='DescribeDBLogFiles',
    )

    result = DBLogFileList(
        log_files=log_files,
        count=len(log_files),
        resource_uri='aws-rds://db-instance/{db_instance_identifier}/log',
    )

    return result
