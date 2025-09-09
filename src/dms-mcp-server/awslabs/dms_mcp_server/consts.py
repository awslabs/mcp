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

"""Constants for the Database Migration Service MCP Server."""

from awslabs.dms_mcp_server import __version__


# Default configuration values
DEFAULT_MAX_RECORDS = 20
DEFAULT_AWS_REGION = 'us-east-1'

# Reload options for table reloading
RELOAD_OPTIONS = {'DATA_RELOAD': 'data-reload', 'VALIDATE_ONLY': 'validate-only'}

# Environment variable names
ENV_VARS = {
    'AWS_REGION': 'AWS_REGION',
    'AWS_PROFILE': 'AWS_PROFILE',
    'FASTMCP_LOG_LEVEL': 'FASTMCP_LOG_LEVEL',
}

# Server configuration
SERVER_CONFIG = {
    'NAME': 'awslabs.dms-mcp-server',
    'DESCRIPTION': 'AWS Database Migration Service MCP Server',
    'VERSION': __version__,
}

# Server instructions and documentation
SERVER_INSTRUCTIONS = """
# AWS Database Migration Service (DMS) MCP Server

This MCP server provides comprehensive tools for managing AWS Database Migration Service resources including replication instances, endpoints, replication tasks, and more.

## Key Features

- **Replication Instance Management**: Create, describe, and manage replication instances with Multi-AZ support
- **Endpoint Management**: Create, describe, and test connectivity to source/target database endpoints
- **Replication Task Management**: Create, start, stop, and monitor replication tasks with detailed statistics
- **Connection Testing**: Test connectivity between replication instances and endpoints
- **Table-Level Monitoring**: Get detailed statistics for table replication progress

## Available Tools

### Endpoint Operations
- `describe_endpoints`: List and describe source/target endpoints with filtering
- `create_endpoint`: Create new source or target database endpoints
- `test_connection`: Test connectivity between replication instances and endpoints
- `describe_connections`: List existing connection test results with filtering

### Replication Instance Operations
- `describe_replication_instances`: List and describe DMS replication instances
- `create_replication_instance`: Create new replication instances with Multi-AZ support

### Replication Task Operations
- `describe_replication_tasks`: List and describe replication tasks with detailed filtering
- `create_replication_task`: Create new replication tasks with table mappings and settings
- `start_replication_task`: Start replication tasks (new, resume, or reload)
- `stop_replication_task`: Stop running replication tasks
- `describe_table_statistics`: Get detailed table-level replication statistics
- `reload_replication_task_tables`: Reload specific tables during replication

## Configuration

The server runs in read-only mode by default. To enable write operations, use `--no-read-only-mode`.

### Environment Variables
- `AWS_REGION`: AWS region (default: us-east-1)
- `FASTMCP_LOG_LEVEL`: Logging level (default: WARNING)

### Required IAM Permissions
Your AWS credentials need appropriate DMS permissions including:
- `dms:DescribeReplicationInstances`
- `dms:DescribeEndpoints`
- `dms:DescribeReplicationTasks`
- `dms:DescribeTableStatistics`
- `dms:DescribeConnections`
- `dms:TestConnection`
- `dms:CreateEndpoint` (write mode)
- `dms:CreateReplicationInstance` (write mode)
- `dms:CreateReplicationTask` (write mode)
- `dms:StartReplicationTask` (write mode)
- `dms:StopReplicationTask` (write mode)
- `dms:ReloadTables` (write mode)

## Usage Examples

### List replication instances
```
describe_replication_instances(max_records=20)
```

### Test endpoint connectivity
```
test_connection(
    replication_instance_arn="arn:aws:dms:region:account:rep:instance-id",
    endpoint_arn="arn:aws:dms:region:account:endpoint:endpoint-id"
)
```

### Get table statistics
```
describe_table_statistics(
    replication_task_arn="arn:aws:dms:region:account:task:task-id"
)
```

### Create a replication task (write mode required)
```
create_replication_task(
    replication_task_identifier="my-migration-task",
    source_endpoint_arn="arn:aws:dms:region:account:endpoint:source-id",
    target_endpoint_arn="arn:aws:dms:region:account:endpoint:target-id",
    replication_instance_arn="arn:aws:dms:region:account:rep:instance-id",
    migration_type="full-load-and-cdc",
    table_mappings='{"rules": [{"rule-type": "selection", "rule-id": "1", "rule-name": "1", "object-locator": {"schema-name": "%", "table-name": "%"}, "rule-action": "include"}]}'
)
```
"""
