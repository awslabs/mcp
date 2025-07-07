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

"""awslabs Data Processing MCP Server implementation.

This module implements the DataProcessing MCP Server, which provides tools for managing Amazon Glue, EMR-EC2, Athena, Data Catalog and Crawler
resources through the Model Context Protocol (MCP).

Environment Variables:
    AWS_REGION: AWS region to use for AWS API calls
    AWS_PROFILE: AWS profile to use for credentials
    FASTMCP_LOG_LEVEL: Log level (default: WARNING)
"""

import argparse
from awslabs.aws_dataprocessing_mcp_server.handlers.athena.athena_data_catalog_handler import (
    AthenaDataCatalogHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.athena.athena_query_handler import (
    AthenaQueryHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.athena.athena_workgroup_handler import (
    AthenaWorkGroupHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_ec2_cluster_handler import (
    EMREc2ClusterHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_ec2_instance_handler import (
    EMREc2InstanceHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_ec2_steps_handler import (
    EMREc2StepsHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_catalog_handler import (
    GlueDataCatalogHandler,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP


# Define server instructions and dependencies
SERVER_INSTRUCTIONS = """
# AWS Data Processing MCP Server

This MCP server provides tools for managing AWS data processing services including Glue Data Catalog.
It enables you to create, manage, and monitor data processing workflows.

## Usage Notes

- By default, the server runs in read-only mode. Use the `--allow-write` flag to enable write operations.
- Access to sensitive data requires the `--allow-sensitive-data-access` flag.
- When creating or updating resources, always check for existing resources first to avoid conflicts.
- IAM roles and permissions are critical for data processing services to access data sources and targets.

## Common Workflows

### Setting Up a Data Catalog
1. Create a database: `manage_aws_glue_databases(operation='create-database', database_name='my-database', description='My database')`
2. Create a connection: `manage_aws_glue_connections(operation='create-connection', connection_name='my-connection', connection_input={'ConnectionType': 'JDBC', 'ConnectionProperties': {'JDBC_CONNECTION_URL': 'jdbc:mysql://host:port/db', 'USERNAME': '...', 'PASSWORD': '...'}})`
3. Create a table: `manage_aws_glue_tables(operation='create-table', database_name='my-database', table_name='my-table', table_input={'StorageDescriptor': {'Columns': [{'Name': 'id', 'Type': 'int'}, {'Name': 'name', 'Type': 'string'}], 'Location': 's3://bucket/path'}})`
4. Create partitions: `manage_aws_glue_partitions(operation='create-partition', database_name='my-database', table_name='my-table', partition_values=['2023-01'], partition_input={'StorageDescriptor': {'Location': 's3://bucket/path/year=2023/month=01'}})`

### Exploring the Data Catalog
1. List databases: `manage_aws_glue_databases(operation='list-databases')`
2. List tables in a database: `manage_aws_glue_tables(operation='list-tables', database_name='my-database')`
3. Search for tables: `manage_aws_glue_tables(operation='search-tables', search_text='customer')`
4. Get table details: `manage_aws_glue_tables(operation='get-table', database_name='my-database', table_name='my-table')`
5. List partitions: `manage_aws_glue_partitions(operation='list-partitions', database_name='my-database', table_name='my-table')`

### Updating Data Catalog Resources
1. Update database properties: `manage_aws_glue_databases(operation='update-database', database_name='my-database', description='Updated description')`
2. Update table schema: `manage_aws_glue_tables(operation='update-table', database_name='my-database', table_name='my-table', table_input={'StorageDescriptor': {'Columns': [{'Name': 'id', 'Type': 'int'}, {'Name': 'name', 'Type': 'string'}, {'Name': 'email', 'Type': 'string'}]}})`
3. Update connection properties: `manage_aws_glue_connections(operation='update-connection', connection_name='my-connection', connection_input={'ConnectionProperties': {'JDBC_CONNECTION_URL': 'jdbc:mysql://new-host:port/db'}})`

### Cleaning Up Data Catalog Resources
1. Delete a partition: `manage_aws_glue_partitions(operation='delete-partition', database_name='my-database', table_name='my-table', partition_values=['2023-01'])`
2. Delete a table: `manage_aws_glue_tables(operation='delete-table', database_name='my-database', table_name='my-table')`
3. Delete a connection: `manage_aws_glue_connections(operation='delete-connection', connection_name='my-connection')`
4. Delete a database: `manage_aws_glue_databases(operation='delete-database', database_name='my-database')`


### Setup EMR EC2 Cluster
1. Create a cluster: `manage_aws_emr_clusters(operation='create-cluster', name='SparkCluster', release_label='emr-7.9.0', applications=[{'Name': 'Spark'}], instances={'InstanceGroups': [{'Name': 'Master', 'InstanceRole': 'MASTER', 'InstanceType': 'm5.xlarge', 'InstanceCount': 1}, {'Name': 'Core', 'InstanceRole': 'CORE', 'InstanceType': 'm5.xlarge', 'InstanceCount': 2}], 'Ec2KeyName': 'my-key-pair', 'KeepJobFlowAliveWhenNoSteps': true})`
2. Describe a cluster: `manage_aws_emr_clusters(operation='describe-cluster', cluster_id='j-123ABC456DEF')`
3. Modify cluster concurrency: `manage_aws_emr_clusters(operation='modify-cluster', cluster_id='j-123ABC456DEF', step_concurrency_level=5)`
4. Modify cluster attributes: `manage_aws_emr_clusters(operation='modify-cluster-attributes', cluster_id='j-123ABC456DEF', termination_protected=true)`
5. Terminate clusters: `manage_aws_emr_clusters(operation='terminate-clusters', cluster_ids=['j-123ABC456DEF'])`
6. List clusters: `manage_aws_emr_clusters(operation='list-clusters', cluster_states=['RUNNING', 'WAITING'])`
7. Create security configuration: `manage_aws_emr_clusters(operation='create-security-configuration', security_configuration_name='my-sec-config', security_configuration_json={'EncryptionConfiguration': {'EnableInTransitEncryption': true}})`
8. Delete security configuration: `manage_aws_emr_clusters(operation='delete-security-configuration', security_configuration_name='my-sec-config')`
9. Describe security configuration: `manage_aws_emr_clusters(operation='describe-security-configuration', security_configuration_name='my-sec-config')`
10. List security configurations: `manage_aws_emr_clusters(operation='list-security-configurations')`

### Run EMR EC2 Steps
1. Add steps: `manage_aws_emr_ec2_steps(operation='add-steps', cluster_id='j-123ABC456DEF', steps=[{'Name': 'MyStep', 'ActionOnFailure': 'CONTINUE', 'HadoopJarStep': {'Jar': 'command-runner.jar', 'Args': ['echo', 'hello']}}])`
2. Cancel steps: `manage_aws_emr_ec2_steps(operation='cancel-steps', cluster_id='j-123ABC456DEF', step_ids=['s-123ABC456DEF'])`
3. Describe step: `manage_aws_emr_ec2_steps(operation='describe-step', cluster_id='j-123ABC456DEF', step_id='s-123ABC456DEF')`
4. List steps: `manage_aws_emr_ec2_steps(operation='list-steps', cluster_id='j-123ABC456DEF')`
5. List steps with filters: `manage_aws_emr_ec2_steps(operation='list-steps', cluster_id='j-123ABC456DEF', step_states=['RUNNING', 'COMPLETED'])`

### Manage EMR EC2 Instance Resources
1. Add instance fleet: `manage_aws_emr_ec2_instances(operation='add-instance-fleet', cluster_id='j-123ABC456DEF', instance_fleet={'InstanceFleetType': 'TASK', 'TargetOnDemandCapacity': 2})`
2. Add instance groups: `manage_aws_emr_ec2_instances(operation='add-instance-groups', cluster_id='j-123ABC456DEF', instance_groups=[{'InstanceRole': 'TASK', 'InstanceType': 'm5.xlarge', 'InstanceCount': 2}])`
3. List instance fleets: `manage_aws_emr_ec2_instances(operation='list-instance-fleets', cluster_id='j-123ABC456DEF')`
4. List instances: `manage_aws_emr_ec2_instances(operation='list-instances', cluster_id='j-123ABC456DEF')`
5. List supported instance types: `manage_aws_emr_ec2_instances(operation='list-supported-instance-types', release_label='emr-6.10.0')`
6. Modify instance fleet: `manage_aws_emr_ec2_instances(operation='modify-instance-fleet', cluster_id='j-123ABC456DEF', instance_fleet_id='if-123ABC', instance_fleet_config={'TargetOnDemandCapacity': 4})`
7. Modify instance groups: `manage_aws_emr_ec2_instances(operation='modify-instance-groups', instance_group_configs=[{'InstanceGroupId': 'ig-123ABC', 'InstanceCount': 3}])`

### Running Athena Queries
1. Execute a query: `manage_aws_athena_queries(operation='start-query-execution', query='SELECT * FROM my_table', work_group='my-workgroup')`
2. Get query results: `manage_aws_athena_queries(operation='get-query-results', query_execution_id='query-id')`
3. Get query execution details: `manage_aws_athena_queries(operation='get-query-execution', query_execution_id='query-id')`
4. Stop a running query: `manage_aws_athena_queries(operation='stop-query-execution', query_execution_id='query-id')`
5. Get query runtime statistics: `manage_aws_athena_queries(operation='get-query-runtime-statistics', query_execution_id='query-id')`

### Creating Athena Named Queries
1. Create a named query: `manage_aws_athena_named_queries(operation='create-named-query', name='my-query', database='my-database', query_string='SELECT * FROM my_table', work_group='my-workgroup')`
2. Get a named query: `manage_aws_athena_named_queries(operation='get-named-query', named_query_id='query-id')`
3. Delete a named query: `manage_aws_athena_named_queries(operation='delete-named-query', named_query_id='query-id')`
4. List named queries: `manage_aws_athena_named_queries(operation='list-named-queries', work_group='my-workgroup')`
5. Update a named query: `manage_aws_athena_named_queries(operation='update-named-query', named_query_id='query-id', name='updated-name', query_string='SELECT * FROM my_table LIMIT 10')`

### Athena Workgroup and Data Catalog
1. Create a workgroup: `manage_aws_athena_workgroups(operation='create-work-group', work_group_name='my-workgroup', configuration={...})`
2. Manage data catalogs: `manage_aws_athena_data_catalogs(operation='create-data-catalog', name='my-catalog', type='GLUE', parameters={...})`

"""

SERVER_DEPENDENCIES = [
    'pydantic>=2.10.6',
    'loguru>=0.7.0',
    'boto3>=1.34.0',
    'requests>=2.31.0',
    'pyyaml>=6.0.0',
    'cachetools>=5.3.0',
]

# Global reference to the MCP server instance for testing purposes
mcp = None


def create_server():
    """Create and configure the MCP server instance."""
    return FastMCP(
        'awslabs.aws-dataprocessing-mcp-server',
        instructions=SERVER_INSTRUCTIONS,
        dependencies=SERVER_DEPENDENCIES,
    )


def main():
    """Run the MCP server with CLI argument support."""
    global mcp

    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for Data Processing'
    )
    parser.add_argument(
        '--allow-write',
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Enable write access mode (allow mutating operations)',
    )
    parser.add_argument(
        '--allow-sensitive-data-access',
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Enable sensitive data access (required for reading sensitive data like logs, query results, and session details)',
    )

    args = parser.parse_args()

    allow_write = args.allow_write
    allow_sensitive_data_access = args.allow_sensitive_data_access

    # Log startup mode
    mode_info = []
    if not allow_write:
        mode_info.append('read-only mode')
    if not allow_sensitive_data_access:
        mode_info.append('restricted sensitive data access mode')

    mode_str = ' in ' + ', '.join(mode_info) if mode_info else ''
    logger.info(f'Starting Data Processing MCP Server{mode_str}')

    # Create the MCP server instance
    mcp = create_server()

    # Initialize handlers - all tools are always registered, access control is handled within tools
    GlueDataCatalogHandler(
        mcp,
        allow_write=allow_write,
        allow_sensitive_data_access=allow_sensitive_data_access,
    )

    AthenaQueryHandler(
        mcp,
        allow_write=allow_write,
        allow_sensitive_data_access=allow_sensitive_data_access,
    )
    AthenaDataCatalogHandler(
        mcp,
        allow_write=allow_write,
        allow_sensitive_data_access=allow_sensitive_data_access,
    )
    AthenaWorkGroupHandler(
        mcp,
        allow_write=allow_write,
        allow_sensitive_data_access=allow_sensitive_data_access,
    )

    EMREc2ClusterHandler(
        mcp,
        allow_write=allow_write,
        allow_sensitive_data_access=allow_sensitive_data_access,
    )

    EMREc2StepsHandler(
        mcp,
        allow_write=allow_write,
        allow_sensitive_data_access=allow_sensitive_data_access,
    )

    EMREc2InstanceHandler(
        mcp,
        allow_write=allow_write,
        allow_sensitive_data_access=allow_sensitive_data_access,
    )

    # Run server
    mcp.run()

    return mcp


if __name__ == '__main__':
    main()
