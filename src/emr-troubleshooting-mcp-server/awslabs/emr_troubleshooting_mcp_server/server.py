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

"""Amazon EMR Troubleshooting MCP Server.

This module provides the main MCP server implementation for EMR
troubleshooting. It uses the FastMCP framework to expose EMR log analysis
tools via the Model Context Protocol.
"""

import logging
import os

from fastmcp import FastMCP
from loguru import logger as loguru_logger

from .consts import LOG_LEVEL
from .tools import EMRTroubleshootingTools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure loguru
loguru_logger.remove()
loguru_logger.add(
    sink=lambda msg: logging.info(msg), level=os.environ.get('FASTMCP_LOG_LEVEL', LOG_LEVEL)
)

# Create the MCP server instance with comprehensive instructions
mcp = FastMCP(
    'awslabs.emr-troubleshooting-mcp-server',
    instructions="""
# Amazon EMR Troubleshooting MCP Server

This MCP server provides sophisticated EMR log analysis and troubleshooting
capabilities using Amazon Athena for SQL-based pattern matching against a
comprehensive knowledge base of 159 curated EMR issues.

## Available Tools

### analyze_emr_cluster_logs (Primary Tool)
Connects directly to EMR cluster logs in S3 and performs sophisticated
SQL-based analysis using Amazon Athena.
- Analyzes live EMR cluster logs with 159-issue knowledge base
- Uses advanced CROSS JOIN UNNEST patterns for keyword matching
- Returns detailed recommendations with AWS Knowledge Center links
- Execution time: ~17 seconds for complete analysis
- Supports time window filtering (default: last hour)

### analyze_emr_logs
Simple pattern matching for quick issue identification without requiring AWS
credentials.
- Useful for analyzing log snippets or when AWS access is not available
- Matches against the same 159-issue knowledge base
- Returns matched issues with confidence scores
- Ideal for quick analysis of specific log files

## Knowledge Base Coverage
The server includes a comprehensive knowledge base covering:
- Apache Spark (30 issues): Memory errors, RPC timeouts, shuffle failures
- Hadoop YARN (15 issues): Container kills, resource allocation issues
- Hadoop HDFS (12 issues): Corruption, namenode issues, datanode failures
- Apache Hive (18 issues): Metastore problems, OutOfMemoryError
- Apache HBase (25 issues): Region server issues, compaction problems
- Presto (20 issues): Query failures, memory management
- EMR Service (25 issues): Bootstrap failures, cluster startup issues
- EMR SDK (14 issues): API errors, configuration problems
- General Errors/Exceptions: Common patterns across components

## Prerequisites
- EMR cluster with logging enabled to S3
- AWS credentials with permissions for EMR, Athena, and S3
- Business/Enterprise support plan recommended for Knowledge Center access

## Analysis Output
Each detected issue includes:
- Issue summary and detailed description
- Component classification (Spark, YARN, Hadoop, Hive, HBase, etc.)
- Occurrence count and sample log evidence
- AWS Knowledge Center links for official documentation
- Step-by-step resolution instructions

## Usage Examples
- "Analyze EMR cluster j-20FTFQ6AGIYQ5 for any known issues"
- "Check cluster j-ABC123DEF456 logs from the last 2 hours"
- "Analyze these YARN container logs for memory-related errors"
""",
)

# Initialize the EMR troubleshooting tools
emr_tools = EMRTroubleshootingTools()

# Register all EMR troubleshooting tools
emr_tools.register(mcp)


def main():
    """Start the EMR Troubleshooting MCP Server."""
    logger.info('Starting EMR Troubleshooting MCP Server')
    mcp.run()


if __name__ == '__main__':
    main()
