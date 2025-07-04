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

"""Constants for the Prometheus MCP server."""

# Default configuration values
DEFAULT_AWS_REGION = 'us-east-1'
DEFAULT_SERVICE_NAME = 'aps'
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1  # seconds

# API endpoints and paths
API_VERSION_PATH = '/api/v1'

# Logging format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Environment variable names
ENV_AWS_PROFILE = 'AWS_PROFILE'
ENV_AWS_REGION = 'AWS_REGION'
ENV_PROMETHEUS_URL = 'PROMETHEUS_URL'
ENV_AWS_SERVICE_NAME = 'AWS_SERVICE_NAME'
ENV_LOG_LEVEL = 'FASTMCP_LOG_LEVEL'

# Server instructions
SERVER_INSTRUCTIONS = """
# Prometheus MCP Server

This MCP server provides tools for interacting with AWS Managed Prometheus.

## Available Tools

### execute_query
Execute an instant PromQL query against Prometheus.

### execute_range_query
Execute a PromQL range query with start time, end time, and step interval.

### list_metrics
List all available metrics in Prometheus.

### get_server_info
Get information about the Prometheus server configuration.

## Query Tips
- Use clear, specific PromQL queries for best results
- For time series data, use execute_range_query with appropriate time ranges
- Explore available metrics with list_metrics before crafting complex queries
"""
