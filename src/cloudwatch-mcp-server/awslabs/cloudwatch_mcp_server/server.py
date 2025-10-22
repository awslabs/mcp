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

"""awslabs cloudwatch MCP Server implementation."""

import argparse
import os
import sys

from awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools import CloudWatchAlarmsTools
from awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools import CloudWatchLogsTools
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools import CloudWatchMetricsTools
from loguru import logger
from mcp.server.fastmcp import FastMCP


def create_mcp_server(host: str = "0.0.0.0", port: int = 8080) -> FastMCP:
    """
    Create and configure the FastMCP server instance.

    Args:
        host: Host to bind to (for HTTP transport)
        port: Port to bind to (for HTTP transport)

    Returns:
        Configured FastMCP instance
    """
    mcp = FastMCP(
        'awslabs.cloudwatch-mcp-server',
        instructions='Use this MCP server to run read-only commands and analyze CloudWatch Logs, Metrics, and Alarms. Supports discovering log groups, running CloudWatch Log Insight Queries, retrieving CloudWatch Metrics information, and getting active alarms with region information. With CloudWatch Logs Insights, you can interactively search and analyze your log data. With CloudWatch Metrics, you can get information about system and application metrics. With CloudWatch Alarms, you can retrieve all currently active alarms for operational awareness, with clear indication of which AWS region was checked.',
        dependencies=[
            'pydantic',
            'loguru',
        ],
        host=host,
        port=port
    )

    # Initialize and register CloudWatch tools
    try:
        cloudwatch_logs_tools = CloudWatchLogsTools()
        cloudwatch_logs_tools.register(mcp)
        logger.info('CloudWatch Logs tools registered successfully')
        cloudwatch_metrics_tools = CloudWatchMetricsTools()
        cloudwatch_metrics_tools.register(mcp)
        logger.info('CloudWatch Metrics tools registered successfully')
        cloudwatch_alarms_tools = CloudWatchAlarmsTools()
        cloudwatch_alarms_tools.register(mcp)
        logger.info('CloudWatch Alarms tools registered successfully')
    except Exception as e:
        logger.error(f'Error initializing CloudWatch tools: {str(e)}')
        raise

    logger.info('MCP server created and tools registered')
    return mcp


def main():
    """Run the MCP server."""
    parser = argparse.ArgumentParser(
        description="AWS CloudWatch MCP Server"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default=os.getenv("MCP_TRANSPORT", "stdio"),
        help="Transport mode (default: stdio, can be set via MCP_TRANSPORT env var)"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HOST", "0.0.0.0"),
        help="Host to bind to for HTTP transport (default: 0.0.0.0, can be set via MCP_HOST env var)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", "8080")),
        help="Port to bind to for HTTP transport (default: 8080, can be set via MCP_PORT env var)"
    )

    args = parser.parse_args()

    logger.info(
        "Starting AWS CloudWatch MCP Server",
        extra={
            "transport": args.transport,
            "host": args.host if args.transport == "streamable-http" else None,
            "port": args.port if args.transport == "streamable-http" else None,
        }
    )

    # Create MCP server
    if args.transport == "streamable-http":
        logger.info(
            f"Starting HTTP server on {args.host}:{args.port}",
            extra={"host": args.host, "port": args.port}
        )
        mcp = create_mcp_server(host=args.host, port=args.port)
        mcp.run(transport="streamable-http")
    else:
        # For stdio transport (default behavior)
        logger.info("Starting stdio transport")
        mcp = create_mcp_server()
        mcp.run(transport="stdio")


if __name__ == '__main__':
    main()