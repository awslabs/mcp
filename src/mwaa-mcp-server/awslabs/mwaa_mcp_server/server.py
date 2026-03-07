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

"""awslabs MWAA MCP Server implementation.

This module implements the MWAA MCP Server, which provides tools for managing Amazon MWAA
environments and Airflow workflows through the Model Context Protocol (MCP).

Environment Variables:
    AWS_REGION: AWS region to use for AWS API calls
    AWS_PROFILE: AWS profile to use for credentials
    MWAA_ENVIRONMENT: Default MWAA environment name (avoids per-call specification)
    FASTMCP_LOG_LEVEL: Log level (default: WARNING)
"""

import argparse
from awslabs.mwaa_mcp_server.airflow_tools import AirflowTools
from awslabs.mwaa_mcp_server.environment_tools import EnvironmentTools
from loguru import logger
from mcp.server.fastmcp import FastMCP


SERVER_INSTRUCTIONS = """
# Amazon MWAA MCP Server

This MCP server provides tools for managing Amazon Managed Workflows for Apache Airflow (MWAA)
environments and interacting with Airflow workflows via the AWS-native invoke_rest_api.

## IMPORTANT: Use MCP Tools for MWAA Operations

Always use the MCP tools provided by this server for MWAA and Airflow operations instead of
direct AWS CLI or Airflow CLI commands.

## Usage Notes

- By default, the server runs in read-only mode. Use the `--allow-write` flag to enable write
  operations such as triggering DAG runs or pausing/unpausing DAGs.
- Set the `MWAA_ENVIRONMENT` environment variable to specify a default environment name. This
  avoids having to pass `environment_name` on every tool call and eliminates errors when multiple
  environments exist in a region.
- All Airflow API operations go through AWS invoke_rest_api — no CLI or web tokens are exposed.
- Connection passwords and extra fields are automatically redacted in responses.

## Common Workflows

### Investigating a Failed DAG Run
1. List recent DAG runs: `list-dag-runs(environment_name='my-env', dag_id='my-dag')`
2. Get the failed run details: `get-dag-run(environment_name='my-env', dag_id='my-dag', dag_run_id='...')`
3. List task instances: `list-task-instances(environment_name='my-env', dag_id='my-dag', dag_run_id='...')`
4. Get task logs: `get-task-logs(environment_name='my-env', dag_id='my-dag', dag_run_id='...', task_id='...', try_number=1)`

### Monitoring Environment Health
1. List environments: `list-environments()`
2. Get environment details: `get-environment(environment_name='my-env')`
3. Check for import errors: `get-import-errors(environment_name='my-env')`
4. List DAGs: `list-dags(environment_name='my-env')`

### Triggering a DAG Run (requires --allow-write)
1. Unpause the DAG if needed: `unpause-dag(environment_name='my-env', dag_id='my-dag')`
2. Trigger the run: `trigger-dag-run(environment_name='my-env', dag_id='my-dag')`
3. Monitor progress: `get-dag-run(environment_name='my-env', dag_id='my-dag', dag_run_id='...')`

## Best Practices

- Use descriptive environment names to make them easier to identify.
- Monitor DAG import errors regularly to catch parsing issues early.
- Check task logs when troubleshooting failed DAG runs.
- Use read-only mode (default) for monitoring and investigation workflows.
- Only enable write access when you need to trigger runs or modify DAG state.
"""

SERVER_DEPENDENCIES = [
    'pydantic',
    'loguru',
    'boto3',
    'botocore',
]

# Global reference to the MCP server instance for testing purposes
mcp = None


def create_server():
    """Create and configure the MCP server instance."""
    return FastMCP(
        'awslabs.mwaa-mcp-server',
        instructions=SERVER_INSTRUCTIONS,
        dependencies=SERVER_DEPENDENCIES,
    )


def main():
    """Run the MCP server with CLI argument support."""
    global mcp

    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for Amazon MWAA'
    )
    parser.add_argument(
        '--allow-write',
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Enable write access mode (allow mutating operations)',
    )

    args = parser.parse_args()

    allow_write = args.allow_write

    mode_str = ' in read-only mode' if not allow_write else ''
    logger.info(f'Starting MWAA MCP Server{mode_str}')

    mcp = create_server()

    EnvironmentTools(mcp, allow_write)
    AirflowTools(mcp, allow_write)

    mcp.run()

    return mcp


if __name__ == '__main__':
    main()
