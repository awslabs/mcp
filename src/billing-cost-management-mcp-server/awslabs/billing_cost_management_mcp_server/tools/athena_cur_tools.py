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
AWS Athena Cost & Usage Report tools for the AWS Billing and Cost Management MCP Server.

Updated to use shared utility functions.
"""

import time
from typing import Any, Dict, Optional
from fastmcp import Context, FastMCP
from ..utilities.aws_service_base import (
    create_aws_client,
    handle_aws_error,
    format_response
)

# Global configuration storage
_athena_config: Dict[str, Any] = {}

athena_cur_server = FastMCP(
    name="athena-cur-tools",
    instructions="Tools for querying AWS Cost & Usage Reports via Amazon Athena"
)


async def _execute_athena_query(ctx: Context, athena_client: Any, query: str) -> Dict[str, Any]:
    """Helper function to execute Athena queries"""
    try:
        # Prepare query execution parameters
        execution_params = {
            "QueryString": query,
            "QueryExecutionContext": {"Database": _athena_config["database"]},
        }

        # Add workgroup or result configuration
        if _athena_config.get("workgroup"):
            execution_params["WorkGroup"] = _athena_config["workgroup"]
        else:
            execution_params["ResultConfiguration"] = {
                "OutputLocation": _athena_config["output_location"]
            }

        # Start query execution
        await ctx.info(f"Starting Athena query execution: {query[:100]}...")
        response = athena_client.start_query_execution(**execution_params)
        query_execution_id = response["QueryExecutionId"]

        # Wait for query to complete
        max_wait_time = _athena_config.get("max_wait_time", 300)
        wait_interval = 2
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            execution_response = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
            status = execution_response["QueryExecution"]["Status"]["State"]

            if status == "SUCCEEDED":
                break
            elif status in ["FAILED", "CANCELLED"]:
                error_message = execution_response["QueryExecution"]["Status"].get(
                    "StateChangeReason", "Unknown error"
                )
                return format_response("error", {}, f"Query {status.lower()}: {error_message}")

            time.sleep(wait_interval)
            elapsed_time += wait_interval
            
            # Log progress every 30 seconds
            if elapsed_time % 30 == 0:
                await ctx.info(f"Waiting for query completion... ({elapsed_time}s elapsed)")

        if elapsed_time >= max_wait_time:
            return format_response("error", {}, f"Query timed out after {max_wait_time} seconds")

        # Get query results
        await ctx.info("Query succeeded, fetching results...")
        results_response = athena_client.get_query_results(
            QueryExecutionId=query_execution_id, MaxResults=1000
        )

        # Format results
        column_info = results_response["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]
        rows = results_response["ResultSet"]["Rows"]

        columns = [col["Name"] for col in column_info]
        formatted_rows = []
        for row in rows[1:]:  # Skip header row
            row_data: Dict[str, Any] = {}
            for i, data in enumerate(row["Data"]):
                row_data[columns[i]] = data.get("VarCharValue", "")
            formatted_rows.append(row_data)

        return format_response(
            "success", 
            {
                "columns": columns, 
                "rows": formatted_rows,
                "row_count": len(formatted_rows)
            }
        )
    
    except Exception as e:
        return await handle_aws_error(ctx, e, "execute_athena_query", "Athena")


@athena_cur_server.tool(
    name="athena_cur_configure",
    description="""Configure Athena settings for Cost & Usage Report queries.

IMPORTANT: You MUST ask the user to provide the following configuration values before calling this tool:

REQUIRED from user:
- database: The Athena database name where their CUR data is stored
- table: The CUR table name in that database
- EITHER workgroup name OR S3 output bucket location

OPTIONAL from user:
- max_wait_time: Query timeout in seconds (defaults to 300 if not provided)

DO NOT make up or assume these values. Always ask the user to provide them first.
""",
)
async def athena_cur_configure(
    ctx: Context,
    database: str,
    table: str,
    workgroup: Optional[str] = None,
    output_location: Optional[str] = None,
    max_wait_time: int = 300,
) -> Dict[str, Any]:
    """
    Configure Athena settings for CUR queries.

    Args:
        ctx: The MCP context object
        database: Athena database name
        table: CUR table name
        workgroup: Athena workgroup name
        output_location: S3 location for query results
        max_wait_time: Maximum wait time for queries

    Returns:
        Dict containing the updated configuration
    """
    try:
        # Validate that either workgroup or output_location is provided
        if not workgroup and not output_location:
            return format_response(
                "error", 
                {}, 
                "Either workgroup or output_location must be provided"
            )

        # Update global configuration
        _athena_config.update(
            {
                "database": database,
                "table": table,
                "workgroup": workgroup,
                "output_location": output_location,
                "max_wait_time": max_wait_time,
            }
        )

        await ctx.info(f"Athena configuration updated: database={database}, table={table}")

        # Create Athena client using shared utility
        athena_client = create_aws_client("athena", region_name="us-east-1")

        # Get table schema
        schema_query = f"DESCRIBE {table}"
        schema_result = await _execute_athena_query(ctx, athena_client, schema_query)

        # Get sample data
        sample_query = f"SELECT * FROM {table} LIMIT 10"
        sample_result = await _execute_athena_query(ctx, athena_client, sample_query)

        if schema_result.get("status") == "error" or sample_result.get("status") == "error":
            error_message = schema_result.get("message") or sample_result.get("message")
            return format_response(
                "error", 
                {}, 
                f"Error testing Athena configuration: {error_message}"
            )

        return format_response(
            "success",
            {
                "configuration": _athena_config.copy(),
                "table_schema": schema_result.get("data", {}).get("rows", []),
                "sample_data": sample_result.get("data", {}).get("rows", []),
            },
            "Athena configuration updated and tested successfully"
        )

    except Exception as e:
        return await handle_aws_error(ctx, e, "athena_cur_configure", "Athena")


@athena_cur_server.tool(
    name="athena_cur_query",
    description="""Query AWS Cost & Usage Report data using Amazon Athena.

PREREQUISITE: User must have configured Athena settings using athena_cur_configure first.
If not configured, this tool will return an error asking them to configure first.

Parameters:
- query: SQL query to execute against the CUR data
- max_results: Maximum number of results to return (optional)

Example queries (replace {table} with actual table name from configuration):
- "SELECT line_item_usage_type, SUM(line_item_unblended_cost) as cost FROM {table} WHERE year='2024' AND month='01' GROUP BY line_item_usage_type ORDER BY cost DESC LIMIT 10"
- "SELECT product_servicename, SUM(line_item_unblended_cost) as total_cost FROM {table} WHERE year='2024' GROUP BY product_servicename ORDER BY total_cost DESC"
""",
)
async def athena_cur_query(
    ctx: Context, query: str, max_results: Optional[int] = None
) -> Dict[str, Any]:
    """
    Execute a SQL query against AWS Cost & Usage Report data via Athena.
    Uses the configuration set by athena_cur_configure.

    Args:
        ctx: The MCP context object
        query: SQL query to execute
        max_results: Maximum number of results to return

    Returns:
        Dict containing the query results
    """
    try:
        await ctx.info(f"Executing Athena CUR query: {query[:100]}...")

        # Check if configuration exists
        if not _athena_config:
            return format_response(
                "error", 
                {}, 
                "Athena not configured. Please run athena_cur_configure first."
            )

        # Create Athena client using shared utility
        athena_client = create_aws_client("athena", region_name="us-east-1")
        result = await _execute_athena_query(ctx, athena_client, query)

        if result["status"] == "error":
            return result

        if result["status"] == "error":
            return result

        # Limit results if specified
        data = result.get("data", {})
        rows = data.get("rows", [])
        
        if max_results and len(rows) > max_results:
            data["rows"] = rows[:max_results]
            data["row_count"] = max_results
            
        return result

    except Exception as e:
        return await handle_aws_error(ctx, e, "athena_cur_query", "Athena")