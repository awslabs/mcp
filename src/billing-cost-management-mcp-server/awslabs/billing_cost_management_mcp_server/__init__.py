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

"""
AWS Billing and Cost Management MCP Server package.

This Model Context Protocol (MCP) server provides tools for AWS cost optimization
by wrapping boto3 SDK functions for AWS cost optimization services.
"""

__version__ = '0.0.2'

# We don't import server here to avoid circular imports

# Import utilities for convenience
from .utilities.aws_service_base import (
    create_aws_client,
    parse_json,
    get_date_range,
    validate_date_format,
    handle_aws_error,
    paginate_aws_response,
    format_response,
)

# Import SQL utilities
from .utilities.sql_utils import (
    get_session_db_path,
    get_db_connection,
    create_table,
    insert_data,
    execute_query,
    convert_api_response_to_table,
    execute_session_sql,
)
