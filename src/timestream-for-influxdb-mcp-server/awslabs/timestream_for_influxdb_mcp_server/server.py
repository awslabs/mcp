# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""awslabs Timestream for InfluxDB MCP Server implementation."""

import boto3
import os
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import ASYNCHRONOUS, SYNCHRONOUS
from loguru import logger
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List, Optional


mcp = FastMCP(
    'awslabs.timestream-for-influxdb-mcp-server',
    instructions="""
    This MCP server provides tools to interact with AWS Timestream for InfluxDB APIs.
    It allows you to create and manage databases, users, and perform other operations
    related to Timestream for InfluxDB service.
    """,
    dependencies=['loguru', 'boto3', 'influxdb-client'],
)


def get_timestream_influxdb_client():
    """Get the AWS Timestream for InfluxDB client."""
    aws_region: str = os.environ.get('AWS_REGION', 'us-east-1')
    aws_profile = os.environ.get('AWS_PROFILE')
    try:
        if aws_profile:
            logger.info(f'Using AWS profile for AWS Timestream Influx Client: {aws_profile}')
            client = boto3.Session(profile_name=aws_profile, region_name=aws_region).client(
                'timestream-influxdb'
            )
        else:
            client = boto3.Session(region_name=aws_region).client('timestream-influxdb')
    except Exception as e:
        logger.error(f'Error creating AWS Timestream for InfluxDB client: {str(e)}')
        raise

    return client


def get_influxdb_client(url, token, org=None, timeout=10000, verify_ssl: bool = True):
    """Get an InfluxDB client.

    Args:
        url: The URL of the InfluxDB server e.g. https://<host-name>:8086.
        token: The authentication token.
        org: The organization name.
        timeout: The timeout in milliseconds.
        verify_ssl: whether to verify SSL with https connections

    Returns:
        An InfluxDB client.
    """
    return InfluxDBClient(url=url, token=token, org=org, timeout=timeout, verify_ssl=verify_ssl)


@mcp.tool(name='CreateDbCluster')
async def create_db_cluster(
    name: str,
    db_instance_type: str,
    password: str,
    allocated_storage_gb: int,
    vpc_security_group_ids: List[str],
    vpc_subnet_ids: List[str],
    publicly_accessible: bool = True,
    username: Optional[str] = None,
    organization: Optional[str] = None,
    bucket: Optional[str] = None,
    db_storage_type: Optional[str] = None,
    deployment_type: Optional[str] = None,
    networkType: Optional[str] = None,
    port: Optional[int] = None,
    db_parameter_group_identifier: Optional[str] = None,
    failover_mode: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    log_delivery_configuration: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a new Timestream for InfluxDB database cluster.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_CreateDbCluster.html

    Args:
        name: The name that uniquely identifies the DB cluster when interacting with the Amazon Timestream for
              InfluxDB API and CLI commands. This name will also be a prefix included in the endpoint.
        db_instance_type: The Timestream for InfluxDB DB instance type to run InfluxDB on.
        password: The password of the initial admin user created in InfluxDB. This password will allow you to
                  access the InfluxDB UI to perform various administrative task and also use the InfluxDB CLI to
                  create an operator token.
        allocated_storage_gb: The amount of storage to allocate for your DB storage type in GiB (gibibytes).
        vpc_security_group_ids: A list of VPC security group IDs to associate with the DB cluster.
        vpc_subnet_ids: A list of VPC subnet IDs to associate with the DB cluster. Provide at least two VPC subnet
                        IDs in different Availability Zones when deploying with a Multi-AZ standby.
        publicly_accessible: Configures the DB cluster with a public IP to facilitate access from outside the VPC.
        username: The username of the initial admin user created in InfluxDB.
        organization: The name of the initial organization for the initial admin user in InfluxDB.
        bucket: The name of the initial InfluxDB bucket.
        db_storage_type: The Timestream for InfluxDB DB storage type to read and write InfluxDB data.
        deployment_type: Specifies the type of cluster to create.
        networkType: Specifies whether the network type of the Timestream for InfluxDB cluster is IPv4 or DUAL.
        port: The port number on which InfluxDB accepts connections. Default: 8086
        db_parameter_group_identifier: The ID of the DB parameter group to assign to your DB cluster.
        failover_mode: Specifies the behavior of failure recovery when the primary node of the cluster fails.
        tags: A list of tags to assign to the DB cluster.
        log_delivery_configuration: Configuration for sending InfluxDB engine logs to a specified S3 bucket.

    Returns:
        Details of the created DB cluster.
    """
    ts_influx_client = get_timestream_influxdb_client()

    # Required parameters
    params = {
        'name': name,
        'dbInstanceType': db_instance_type,
        'password': password,
        'vpcSecurityGroupIds': vpc_security_group_ids,
        'vpcSubnetIds': vpc_subnet_ids,
        'allocatedStorage': allocated_storage_gb,
        'publiclyAccessible': publicly_accessible,
    }

    # Add optional parameters if provided
    if db_parameter_group_identifier:
        params['dbParameterGroupIdentifier'] = db_parameter_group_identifier
    if username:
        params['username'] = username
    if organization:
        params['organization'] = organization
    if bucket:
        params['bucket'] = bucket
    if port:
        params['port'] = port
    if db_storage_type:
        params['dbStorageType'] = db_storage_type
    if deployment_type:
        params['deploymentType'] = deployment_type
    if networkType:
        params['networkType'] = networkType
    if failover_mode:
        params['failoverMode'] = failover_mode
    if log_delivery_configuration:
        params['logDeliveryConfiguration'] = log_delivery_configuration

    if tags:
        tag_list = [{'Key': k, 'Value': v} for k, v in tags.items()]
        params['tags'] = tag_list

    try:
        response = ts_influx_client.create_db_cluster(**params)
        return response
    except Exception as e:
        logger.error(f'Error creating DB cluster: {str(e)}')
        raise e


@mcp.tool(name='CreateDbInstance')
async def create_db_instance(
    db_instance_name: str,
    db_instance_type: str,
    password: str,
    allocated_storage_gb: int,
    vpc_security_group_ids: List[str],
    vpc_subnet_ids: List[str],
    publicly_accessible: bool = False,
    username: Optional[str] = None,
    organization: Optional[str] = None,
    bucket: Optional[str] = None,
    db_storage_type: Optional[str] = None,
    deployment_type: Optional[str] = None,
    networkType: Optional[str] = None,
    port: Optional[int] = None,
    db_parameter_group_id: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Create a new Timestream for InfluxDB database instance.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_CreateDbInstance.html#tsinfluxdb-CreateDbInstance-request-dbStorageType

    Args:
        db_instance_name: The name that uniquely identifies the DB instance. This name will also be a prefix included
                          in the endpoint. DB instance names must be unique per customer and per region.
        db_instance_type: The Timestream for InfluxDB DB instance type to run InfluxDB on. The instance-type is
                          prefixed with 'db.influx'
        password: The password of the initial admin user created in InfluxDB. This password will allow you to
                  access the InfluxDB UI to perform various administrative task and also use the InfluxDB CLI to
                  create an operator token. These attributes will be stored in a Secret created in AWS Secrets Manager
                  in your account.
        username: The username of the initial admin user created in InfluxDB. This username will allow you to access
                  the InfluxDB UI to perform various administrative tasks and also use the InfluxDB CLI to create an
                  operator token. These attributes will be stored in a Secret created in Amazon Secrets Manager
                  in your account.
        organization: The name of the initial organization for the initial admin user in InfluxDB. An InfluxDB
                      organization is a workspace for a group of users.
        bucket: The name of the initial InfluxDB bucket. All InfluxDB data is stored in a bucket. A bucket combines
                the concept of a database and a retention period (the duration of time that each data point persists).
                A bucket belongs to an organization.
        vpc_security_group_ids: A list of VPC security group IDs to associate with the DB instance.
        vpc_subnet_ids: A list of VPC subnet IDs to associate with the DB instance. Provide at least two VPC subnet
                        IDs in different availability zones when deploying with a Multi-AZ standby.
        publicly_accessible: Configures the DB instance with a public IP to facilitate access.
        allocated_storage_gb: The amount of storage to allocate for your DB storage type in GiB (gibibytes).
        db_parameter_group_id: The id of the DB parameter group to assign to your DB instance. DB parameter groups
                               specify how the database is configured. For example, DB parameter groups can specify
                               the limit for query concurrency.
        port: The port number on which InfluxDB accepts connections. Default: 8086
        db_storage_type: The Timestream for InfluxDB DB storage type to read and write InfluxDB data.
        deployment_type: Specifies whether the DB instance will be deployed as a standalone instance or with a
                         Multi-AZ standby for high availability.
        networkType: Specifies whether the networkType of the Timestream for InfluxDB instance is IPV4, which can
                     communicate over IPv4 protocol only, or DUAL, which can communicate over both IPv4 and IPv6
                    protocols.
        tags: A list of tags to assign to the DB instance.

    Returns:
        Details of the created DB instance.
    """
    ts_influx_client = get_timestream_influxdb_client()

    # Required parameters
    params = {
        'name': db_instance_name,
        'dbInstanceType': db_instance_type,
        'password': password,
        'vpcSecurityGroupIds': vpc_security_group_ids,
        'vpcSubnetIds': vpc_subnet_ids,
        'allocatedStorage': allocated_storage_gb,
        'publiclyAccessible': publicly_accessible,
    }

    # Add optional parameters if provided
    if db_parameter_group_id:
        params['dbParameterGroupIdentifier'] = db_parameter_group_id
    if username:
        params['username'] = username
    if organization:
        params['organization'] = organization
    if bucket:
        params['bucket'] = bucket
    if port:
        params['port'] = port
    if username:
        params['username'] = username
    if db_storage_type:
        params['db_storage_type'] = db_storage_type
    if deployment_type:
        params['deployment_type'] = deployment_type
    if networkType:
        params['networkType'] = networkType

    if tags:
        tag_list = [{'Key': k, 'Value': v} for k, v in tags.items()]
        params['Tags'] = tag_list

    try:
        response = ts_influx_client.create_db_instance(**params)
        return response
    except Exception as e:
        logger.error(f'Error creating DB instance: {str(e)}')
        raise e


@mcp.tool(name='LsInstancesOfCluster')
async def list_db_instances_for_cluster(
    db_cluster_id: str, next_token: Optional[str] = None, max_results: Optional[int] = None
) -> Dict[str, Any]:
    """Returns a list of Timestream for InfluxDB DB instances belonging to a specific cluster.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_ListDbInstancesForCluster.html

    Args:
        db_cluster_id: Service-generated unique identifier of the DB cluster.
        next_token: The pagination token. To resume pagination, provide the nextToken value as an argument of a subsequent API invocation.
        max_results: The maximum number of items to return in the output. If the total number of items available is more than the value specified, a nextToken is provided in the output.

    Returns:
        A list of Timestream for InfluxDB instance summaries belonging to the cluster.
    """
    ts_influx_client = get_timestream_influxdb_client()

    params = {'dbClusterId': db_cluster_id}

    if next_token:
        params['nextToken'] = next_token
    if max_results:
        params['maxResults'] = max_results

    try:
        response = ts_influx_client.list_db_instances_for_cluster(**params)
        return response
    except Exception as e:
        logger.error(f'Error listing DB instances for cluster: {str(e)}')
        raise e


@mcp.tool(name='ListDbInstances')
async def list_db_instances(
    next_token: Optional[str] = None, max_results: Optional[int] = None
) -> Dict[str, Any]:
    """Returns a list of Timestream for InfluxDB DB instances.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_ListDbInstances.html

    Args:
        next_token: The pagination token. To resume pagination, provide the NextToken value as argument of a subsequent API invocation.
        max_results: The maximum number of items to return in the output. If the total number of items available is more than the value specified, a NextToken is provided in the output.

    Returns:
        A list of Timestream for InfluxDB DB instance summaries.
    """
    ts_influx_client = get_timestream_influxdb_client()

    params = {}
    if next_token:
        params['nextToken'] = next_token
    if max_results:
        params['maxResults'] = max_results

    try:
        response = ts_influx_client.list_db_instances(**params)
        return response
    except Exception as e:
        logger.error(f'Error listing DB instances: {str(e)}')
        raise e


@mcp.tool(name='ListDbClusters')
async def list_db_clusters(
    next_token: Optional[str] = None, max_results: Optional[int] = None
) -> Dict[str, Any]:
    """Returns a list of Timestream for InfluxDB DB clusters.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_ListDbClusters.html

    Args:
        next_token: The pagination token. To resume pagination, provide the nextToken value as an argument of a subsequent API invocation.
        max_results: The maximum number of items to return in the output. If the total number of items available is more than the value specified, a nextToken is provided in the output.

    Returns:
        A list of Timestream for InfluxDB cluster summaries.
    """
    ts_influx_client = get_timestream_influxdb_client()

    params = {}
    if next_token:
        params['nextToken'] = next_token
    if max_results:
        params['maxResults'] = max_results

    try:
        response = ts_influx_client.list_db_clusters(**params)
        return response
    except Exception as e:
        logger.error(f'Error listing DB clusters: {str(e)}')
        raise e


@mcp.tool(name='GetDbParameterGroup')
async def get_db_parameter_group(identifier: str) -> Dict[str, Any]:
    """Returns a Timestream for InfluxDB DB parameter group.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_GetDbParameterGroup.html

    Args:
        identifier: The id of the DB parameter group.

    Returns:
        Details of the DB parameter group.
    """
    ts_influx_client = get_timestream_influxdb_client()

    try:
        response = ts_influx_client.get_db_parameter_group(identifier=identifier)
        return response
    except Exception as e:
        logger.error(f'Error getting DB parameter group: {str(e)}')
        raise e


@mcp.tool(name='GetDbInstance')
async def get_db_instance(identifier: str) -> Dict[str, Any]:
    """Returns a Timestream for InfluxDB DB instance.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_GetDbInstance.html

    Args:
        identifier: The id of the DB instance.

    Returns:
        Details of the DB instance.
    """
    ts_influx_client = get_timestream_influxdb_client()

    try:
        response = ts_influx_client.get_db_instance(identifier=identifier)
        return response
    except Exception as e:
        logger.error(f'Error getting DB instance: {str(e)}')
        raise e


@mcp.tool(name='GetDbCluster')
async def get_db_cluster(db_cluster_id: str) -> Dict[str, Any]:
    """Retrieves information about a Timestream for InfluxDB cluster.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_GetDbCluster.html

    Args:
        db_cluster_id: Service-generated unique identifier of the DB cluster to retrieve.

    Returns:
        Details of the DB cluster.
    """
    ts_influx_client = get_timestream_influxdb_client()

    try:
        response = ts_influx_client.get_db_cluster(dbClusterId=db_cluster_id)
        return response
    except Exception as e:
        logger.error(f'Error getting DB cluster: {str(e)}')
        raise e


@mcp.tool(name='DeleteDbInstance')
async def delete_db_instance(identifier: str) -> Dict[str, Any]:
    """Deletes a Timestream for InfluxDB DB instance.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_DeleteDbInstance.html

    Args:
        identifier: The id of the DB instance.

    Returns:
        Details of the deleted DB instance.
    """
    ts_influx_client = get_timestream_influxdb_client()

    try:
        response = ts_influx_client.delete_db_instance(identifier=identifier)
        return response
    except Exception as e:
        logger.error(f'Error deleting DB instance: {str(e)}')
        raise e


@mcp.tool(name='DeleteDbCluster')
async def delete_db_cluster(db_cluster_id: str) -> Dict[str, Any]:
    """Deletes a Timestream for InfluxDB cluster.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_DeleteDbCluster.html

    Args:
        db_cluster_id: Service-generated unique identifier of the DB cluster.

    Returns:
        Details of the deleted DB cluster.
    """
    ts_influx_client = get_timestream_influxdb_client()

    try:
        response = ts_influx_client.delete_db_cluster(dbClusterId=db_cluster_id)
        return response
    except Exception as e:
        logger.error(f'Error deleting DB cluster: {str(e)}')
        raise e


@mcp.tool(name='ListDbParamGroups')
async def list_db_parameter_groups(
    next_token: Optional[str] = None, max_results: Optional[int] = None
) -> Dict[str, Any]:
    """Returns a list of Timestream for InfluxDB DB parameter groups.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_ListDbParameterGroups.html

    Args:
        next_token: The pagination token. To resume pagination, provide the NextToken value as argument of a subsequent API invocation.
        max_results: The maximum number of items to return in the output. If the total number of items available is more than the value specified, a NextToken is provided in the output.

    Returns:
        A list of Timestream for InfluxDB DB parameter group summaries.
    """
    ts_influx_client = get_timestream_influxdb_client()

    params = {}
    if next_token:
        params['nextToken'] = next_token
    if max_results:
        params['maxResults'] = max_results

    try:
        response = ts_influx_client.list_db_parameter_groups(**params)
        return response
    except Exception as e:
        logger.error(f'Error listing DB parameter groups: {str(e)}')
        raise e


@mcp.tool(name='ListTagsForResource')
async def list_tags_for_resource(resource_arn: str) -> Dict[str, Any]:
    """A list of tags applied to the resource.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_ListTagsForResource.html

    Args:
        resource_arn: The Amazon Resource Name (ARN) of the tagged resource.

    Returns:
        A list of tags used to categorize and track resources.
    """
    ts_influx_client = get_timestream_influxdb_client()

    try:
        response = ts_influx_client.list_tags_for_resource(resourceArn=resource_arn)
        return response
    except Exception as e:
        logger.error(f'Error listing tags for resource: {str(e)}')
        raise e


@mcp.tool(name='TagResource')
async def tag_resource(resource_arn: str, tags: Dict[str, str]) -> Dict[str, Any]:
    """Tags are composed of a Key/Value pairs. You can use tags to categorize and track your Timestream for InfluxDB resources.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_TagResource.html

    Args:
        resource_arn: The Amazon Resource Name (ARN) of the tagged resource.
        tags: A list of key-value pairs to associate with the resource.

    Returns:
        Status of the tag operation.
    """
    ts_influx_client = get_timestream_influxdb_client()

    # Convert tags dictionary to list of Key/Value pairs
    tag_list = [{'Key': k, 'Value': v} for k, v in tags.items()]

    try:
        response = ts_influx_client.tag_resource(resourceArn=resource_arn, tags=tag_list)
        return response
    except Exception as e:
        logger.error(f'Error tagging resource: {str(e)}')
        raise e


@mcp.tool(name='UntagResource')
async def untag_resource(resource_arn: str, tag_keys: List[str]) -> Dict[str, Any]:
    """Removes the tag from the specified resource.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_UntagResource.html

    Args:
        resource_arn: The Amazon Resource Name (ARN) of the tagged resource.
        tag_keys: The keys used to identify the tags to remove.

    Returns:
        Status of the untag operation.
    """
    ts_influx_client = get_timestream_influxdb_client()

    try:
        response = ts_influx_client.untag_resource(resourceArn=resource_arn, tagKeys=tag_keys)
        return response
    except Exception as e:
        logger.error(f'Error untagging resource: {str(e)}')
        raise e


@mcp.tool(name='UpdateDbCluster')
async def update_db_cluster(
    db_cluster_id: str,
    db_instance_type: Optional[str] = None,
    db_parameter_group_identifier: Optional[str] = None,
    port: Optional[int] = None,
    failover_mode: Optional[str] = None,
    log_delivery_configuration: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Updates a Timestream for InfluxDB cluster.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_UpdateDbCluster.html

    Args:
        db_cluster_id: Service-generated unique identifier of the DB cluster to update.
        db_instance_type: Update the DB cluster to use the specified DB instance Type.
        db_parameter_group_identifier: Update the DB cluster to use the specified DB parameter group.
        port: Update the DB cluster to use the specified port.
        failover_mode: Update the DB cluster's failover behavior.
        log_delivery_configuration: The log delivery configuration to apply to the DB cluster.

    Returns:
        Details of the updated DB cluster.
    """
    ts_influx_client = get_timestream_influxdb_client()

    # Required parameters
    params = {'dbClusterId': db_cluster_id}

    # Add optional parameters if provided
    if db_instance_type:
        params['dbInstanceType'] = db_instance_type
    if db_parameter_group_identifier:
        params['dbParameterGroupIdentifier'] = db_parameter_group_identifier
    if port:
        params['port'] = port
    if failover_mode:
        params['failoverMode'] = failover_mode
    if log_delivery_configuration:
        params['logDeliveryConfiguration'] = log_delivery_configuration

    try:
        response = ts_influx_client.update_db_cluster(**params)
        return response
    except Exception as e:
        logger.error(f'Error updating DB cluster: {str(e)}')
        raise e


@mcp.tool(name='UpdateDbInstance')
async def update_db_instance(
    identifier: str,
    db_instance_type: Optional[str] = None,
    db_parameter_group_identifier: Optional[str] = None,
    port: Optional[int] = None,
    allocated_storage_gb: Optional[int] = None,
    db_storage_type: Optional[str] = None,
    deployment_type: Optional[str] = None,
    log_delivery_configuration: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Updates a Timestream for InfluxDB DB instance.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_UpdateDbInstance.html

    Args:
        identifier: The id of the DB instance.
        db_instance_type: The Timestream for InfluxDB DB instance type to run InfluxDB on.
        db_parameter_group_identifier: The id of the DB parameter group to assign to your DB instance.
        port: The port number on which InfluxDB accepts connections.
        allocated_storage_gb: The amount of storage to allocate for your DB storage type (in gibibytes).
        db_storage_type: The Timestream for InfluxDB DB storage type that InfluxDB stores data on.
        deployment_type: Specifies whether the DB instance will be deployed as a standalone instance or with a Multi-AZ standby for high availability.
        log_delivery_configuration: Configuration for sending InfluxDB engine logs to send to specified S3 bucket.

    Returns:
        Details of the updated DB instance.
    """
    ts_influx_client = get_timestream_influxdb_client()

    # Required parameters
    params = {'identifier': identifier}

    # Add optional parameters if provided
    if db_instance_type:
        params['dbInstanceType'] = db_instance_type
    if db_parameter_group_identifier:
        params['dbParameterGroupIdentifier'] = db_parameter_group_identifier
    if port:
        params['port'] = port
    if allocated_storage_gb:
        params['allocatedStorage'] = allocated_storage_gb
    if db_storage_type:
        params['dbStorageType'] = db_storage_type
    if deployment_type:
        params['deploymentType'] = deployment_type
    if log_delivery_configuration:
        params['logDeliveryConfiguration'] = log_delivery_configuration

    try:
        response = ts_influx_client.update_db_instance(**params)
        return response
    except Exception as e:
        logger.error(f'Error updating DB instance: {str(e)}')
        raise e


@mcp.tool(name='LsInstancesByStatus')
async def list_db_instances_by_status(status: str) -> Dict[str, Any]:
    """Returns a list of Timestream for InfluxDB DB instances filtered by status.

    This tool paginates through all DB instances and filters them by the provided status
    in a case-insensitive manner.

    Args:
        status: The status to filter DB instances by (case-insensitive).

    Returns:
        A list of Timestream for InfluxDB DB instance summaries matching the specified status.
    """
    ts_influx_client = get_timestream_influxdb_client()

    # Convert status to lowercase for case-insensitive comparison
    status_lower = status.lower()

    # Initialize variables for pagination
    next_token = None
    filtered_instances = []

    try:
        # Paginate through all instances
        while True:
            # Prepare parameters for the API call
            params = {}
            if next_token:
                params['nextToken'] = next_token

            # Call the ListDbInstances API
            response = ts_influx_client.list_db_instances(**params)

            # Filter instances by status (case-insensitive)
            if 'items' in response:
                for instance in response['items']:
                    if 'status' in instance and instance['status'].lower() == status_lower:
                        filtered_instances.append(instance)

            # Check if there are more results to fetch
            if 'nextToken' in response and response['nextToken']:
                next_token = response['nextToken']
            else:
                # No more results to fetch
                break

        # Prepare the response
        result = {'items': filtered_instances, 'count': len(filtered_instances)}

        return result
    except Exception as e:
        logger.error(f'Error listing DB instances by status: {str(e)}')
        raise e


@mcp.tool(name='ListClustersByStatus')
async def list_db_clusters_by_status(status: str) -> Dict[str, Any]:
    """Returns a list of Timestream for InfluxDB DB clusters filtered by status.

    This tool paginates through all DB clusters and filters them by the provided status
    in a case-insensitive manner.

    Args:
        status: The status to filter DB clusters by (case-insensitive).

    Returns:
        A list of Timestream for InfluxDB DB cluster summaries matching the specified status.
    """
    ts_influx_client = get_timestream_influxdb_client()

    # Convert status to lowercase for case-insensitive comparison
    status_lower = status.lower()

    # Initialize variables for pagination
    next_token = None
    filtered_clusters = []

    try:
        # Paginate through all clusters
        while True:
            # Prepare parameters for the API call
            params = {}
            if next_token:
                params['nextToken'] = next_token

            # Call the ListDbClusters API
            response = ts_influx_client.list_db_clusters(**params)

            # Filter clusters by status (case-insensitive)
            if 'items' in response:
                for cluster in response['items']:
                    if 'status' in cluster and cluster['status'].lower() == status_lower:
                        filtered_clusters.append(cluster)

            # Check if there are more results to fetch
            if 'nextToken' in response and response['nextToken']:
                next_token = response['nextToken']
            else:
                # No more results to fetch
                break

        # Prepare the response
        result = {'items': filtered_clusters, 'count': len(filtered_clusters)}

        return result
    except Exception as e:
        logger.error(f'Error listing DB clusters by status: {str(e)}')
        raise e


@mcp.tool(name='CreateDbParamGroup')
async def create_db_parameter_group(
    name: str,
    description: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Creates a new Timestream for InfluxDB DB parameter group to associate with DB instances.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_CreateDbParameterGroup.html

    Args:
        name: The name of the DB parameter group. The name must be unique per customer and per region.
        description: A description of the DB parameter group.
        parameters: A list of the parameters that comprise the DB parameter group.
        tags: A list of key-value pairs to associate with the DB parameter group.

    Returns:
        Details of the created DB parameter group.
    """
    ts_influx_client = get_timestream_influxdb_client()

    # Required parameters
    params = {'name': name}

    # Add optional parameters if provided
    if description:
        params['description'] = description
    if parameters:
        params['parameters'] = parameters
    if tags:
        tag_list = [{'Key': k, 'Value': v} for k, v in tags.items()]
        params['tags'] = tag_list

    try:
        response = ts_influx_client.create_db_parameter_group(**params)
        return response
    except Exception as e:
        logger.error(f'Error creating DB parameter group: {str(e)}')
        raise e


@mcp.tool(name='InfluxDBWritePoints')
async def influxdb_write_points(
    url: str,
    token: str,
    bucket: str,
    org: str,
    points: List[Dict[str, Any]],
    write_precision: Optional[str] = None,
    sync_mode: str = 'synchronous',
    verify_ssl: bool = True,
) -> Dict[str, Any]:
    """Write data points to InfluxDB.

    Args:
        url: The URL of the InfluxDB server.
        token: The authentication token.
        bucket: The destination bucket for writes.
        org: The organization name.
        points: List of data points to write. Each point should be a dictionary with:
               - measurement: The measurement name
               - tags: Dictionary of tag keys and values
               - fields: Dictionary of field keys and values
               - time: Optional timestamp (if not provided, current time will be used)
        write_precision: The precision for the unix timestamps within the body line-protocol.
                        One of: ns, us, ms, s (default is ns).
        sync_mode: The synchronization mode, either "synchronous" or "asynchronous".
        verify_ssl: whether to verify SSL with https connections

        Example of points:
        [
           {
             "measurement": "my_measurement",
             "tags": {"location": "Prague"},
             "field": {"temperature": 25.3}
            }
        ]

    Returns:
        Status of the write operation.
    """
    try:
        client = get_influxdb_client(url, token, org, verify_ssl)

        # Set write mode
        if sync_mode.lower() == 'synchronous':
            write_api = client.write_api(write_options=SYNCHRONOUS)
        else:
            write_api = client.write_api(write_options=ASYNCHRONOUS)

        # Convert dictionary points to Point objects
        influx_points = []
        for p in points:
            point = Point(p['measurement'])

            # Add tags
            if 'tags' in p:
                for tag_key, tag_value in p['tags'].items():
                    point = point.tag(tag_key, tag_value)

            # Add fields
            if 'fields' in p:
                for field_key, field_value in p['fields'].items():
                    point = point.field(field_key, field_value)

            # Add time if provided
            if 'time' in p:
                point = point.time(p['time'])

            influx_points.append(point)

        # Write points
        write_api.write(
            bucket=bucket,
            org=org,
            record=influx_points,
            write_precision=write_precision,
            verify_ssl=verify_ssl,
        )

        # Close client
        client.close()

        return {
            'status': 'success',
            'message': f'Successfully wrote {len(points)} points to InfluxDB',
        }
    except Exception as e:
        logger.error(f'Error writing points to InfluxDB: {str(e)}')
        return {'status': 'error', 'message': str(e)}


@mcp.tool(name='InfluxDBWriteLP')
async def influxdb_write_line_protocol(
    url: str,
    token: str,
    bucket: str,
    org: str,
    data_line_protocol: str,
    write_precision: Optional[str] = None,
    sync_mode: str = 'synchronous',
    verify_ssl: bool = True,
) -> Dict[str, Any]:
    """Write data in Line Protocol format to InfluxDB.

    Args:
        url: The URL of the InfluxDB server.
        token: The authentication token.
        bucket: The destination bucket for writes.
        org: The organization name.
        data_line_protocol: Data in InfluxDB Line Protocol format.
        write_precision: The precision for the unix timestamps within the body line-protocol.
                        One of: ns, us, ms, s (default is ns).
        sync_mode: The synchronization mode, either "synchronous" or "asynchronous".
        verify_ssl: whether to verify SSL with https connections

    Returns:
        Status of the write operation.
    """
    try:
        client = get_influxdb_client(url, token, org)

        # Set write mode
        if sync_mode.lower() == 'synchronous':
            write_api = client.write_api(write_options=SYNCHRONOUS)
        else:
            write_api = client.write_api(write_options=ASYNCHRONOUS)

        # Write line protocol
        write_api.write(
            bucket=bucket,
            org=org,
            record=data_line_protocol,
            write_precision=write_precision,
            verify_ssl=verify_ssl,
        )

        # Close client
        client.close()

        return {
            'status': 'success',
            'message': 'Successfully wrote line protocol data to InfluxDB',
        }
    except Exception as e:
        logger.error(f'Error writing line protocol to InfluxDB: {str(e)}')
        return {'status': 'error', 'message': str(e)}


@mcp.tool(name='InfluxDBQuery')
async def influxdb_query(
    url: str, token: str, org: str, query: str, verify_ssl: bool = True
) -> Dict[str, Any]:
    """Query data from InfluxDB using Flux query language.

    Args:
        url: The URL of the InfluxDB server.
        token: The authentication token.
        org: The organization name.
        query: The Flux query string.
        verify_ssl: whether to verify SSL with https connections

    Returns:
        Query results in the specified format.
    """
    try:
        client = get_influxdb_client(url, token, org, verify_ssl)
        query_api = client.query_api()

        # Return as JSON
        tables = query_api.query(org=org, query=query)

        # Process the tables into a more usable format
        result = []
        for table in tables:
            for record in table.records:
                result.append(
                    {
                        'measurement': record.get_measurement(),
                        'field': record.get_field(),
                        'value': record.get_value(),
                        'time': record.get_time().isoformat() if record.get_time() else None,
                        'tags': record.values.get('tags', {}),
                    }
                )

        client.close()
        return {'status': 'success', 'result': result, 'format': 'json'}

    except Exception as e:
        logger.error(f'Error querying InfluxDB: {str(e)}')
        return {'status': 'error', 'message': str(e)}


def main():
    """Main entry point for the MCP server application."""
    logger.info('Starting Timestream for InfluxDB MCP Server')
    mcp.run()


if __name__ == '__main__':
    main()
