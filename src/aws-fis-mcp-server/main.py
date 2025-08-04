#!/usr/bin/env python3
"""
AWS Fault Injection Service (FIS) FastMCP Server

Entry point for running the FastMCP server.
"""

import sys
from aws_fis_mcp.server import run_server

if __name__ == "__main__":
    print("AWS FIS MCP Server", file=sys.stderr)
    print("==================", file=sys.stderr)
    run_server()
