#!/usr/bin/env python3
"""
This script starts the MCP server directly by using the Python import
approach.
"""

import argparse
import os
import sys

from awslabs.aws_iot_sitewise_mcp_server.server import main

# Add the project root to the Python path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AWS IoT SiteWise MCP Server")
    parser.add_argument(
        "--allow-writes",
        action="store_true",
        help="Enable write operations (create, update, delete). By default, "
        "server runs in read-only mode.",
    )

    args = parser.parse_args()

    # Set environment variable to pass the flag to the server
    os.environ["SITEWISE_MCP_ALLOW_WRITES"] = str(args.allow_writes)

    if args.allow_writes:
        print("Starting server with WRITE operations enabled...")
    else:
        print(
            "Starting server in READ-ONLY mode. Use --allow-writes to enable "
            "write operations."
        )

    main()
