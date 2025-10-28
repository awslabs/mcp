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

"""Unified SQL tool for the AWS Billing and Cost Management MCP server.

This module provides a unified interface for executing SQL queries against
session data, including AWS API results stored in SQLite.

Updated to use shared utility functions.
"""

import uuid
from ..utilities.aws_service_base import handle_aws_error
from ..utilities.sql_utils import execute_session_sql
from fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional


unified_sql_server = FastMCP(
    name='unified-sql-tools',
    instructions='Unified SQL tool for querying session database and adding user data',
)


@unified_sql_server.tool(
    name='session-sql',
    description="""Execute SQL queries on the persistent session database.

This tool queries tables created by other tools (like cost_explorer_sql) within the current session.
All tools share the same database, allowing cross-tool data analysis and joins.

Use this tool to:
- Query tables created by cost_explorer_sql and other tools
- Join data from multiple AWS APIs
- Perform complex analysis across different data sources

Common queries:
- SELECT name FROM sqlite_master WHERE type='table' -- List all tables
- SELECT * FROM [table_name] LIMIT 10 -- Preview table data""",
)
async def session_sql(
    ctx: Context,
    query: str,
    schema: Optional[List[str]] = None,
    data: Optional[List[List[Any]]] = None,
    table_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute SQL query on the persistent session database, optionally adding user data first.

    Args:
        ctx: The MCP context object
        query: SQL query to execute
        schema: Optional column definitions for user data (e.g. ["service TEXT", "cost REAL"])
        data: Optional array of data rows to add to database before querying
        table_name: Optional name for user data table (auto-generated if not provided)

    Returns:
        Dict containing query results
    """
    try:
        # Generate a table name if one is not provided but data is
        if data and schema and not table_name:
            table_name = f'user_data_{str(uuid.uuid4())[:8]}'

        # Use the shared SQL utility to execute the query
        return await execute_session_sql(ctx, query, schema, data, table_name)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'session_sql', 'SQL')
