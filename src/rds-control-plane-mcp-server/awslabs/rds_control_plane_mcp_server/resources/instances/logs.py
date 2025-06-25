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

"""This module provides functions to list non-empty log files from a database instance."""

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
from typing import Annotated, List


async def list_db_log_files(
    db_instance_identifier: Annotated[
        str, Field(description='The identifier for the DB instance')
    ],
    rds_client: RDSClient,
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
        paginator = rds_client.get_paginator('describe_db_log_files')
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
                        last_written=datetime.fromtimestamp(log_file.get('LastWritten', 0) / 1000),
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
