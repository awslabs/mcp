#!/usr/bin/env python3
"""
AWS Fault Injection Service (FIS) MCP Server

Entry point for running the MCP server as a module.
"""

from aws_fis_mcp.server import run_server

if __name__ == "__main__":
    run_server()
