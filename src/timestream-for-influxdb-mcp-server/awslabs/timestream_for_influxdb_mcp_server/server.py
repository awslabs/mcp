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
from pydantic import Field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


# Define Field parameters as global variables to avoid duplication
# Common fields
REQUIRED_FIELD_DB_CLUSTER_ID = Field(
    ..., description='Service-generated unique identifier of the DB cluster.'
)

REQUIRED_FIELD_DB_INSTANCE_NAME = Field(
    ...,
    description='The name that uniquely identifies the DB instance. '
    'This name will also be a prefix included in the endpoint. '
    'DB instance names must be unique per customer and per region.',
)
REQUIRED_FIELD_DB_INSTANCE_TYPE = Field(
    ..., description='The Timestream for InfluxDB DB instance type to run InfluxDB on.'
)

OPTIONAL_FIELD_DB_INSTANCE_TYPE_CLUSTER_UPDATE = Field(
    None, description='Update the DB cluster to use the specified DB instance Type.'
)

REQUIRED_FIELD_PASSWORD = Field(
    ...,
    description='The password of the initial admin user created in InfluxDB. '
    'This password will allow you to access the InfluxDB UI to perform various administrative task '
    'and also use the InfluxDB CLI to create an operator token.',
)
REQUIRED_FIELD_ALLOCATED_STORAGE_GB = Field(
    ...,
    description='The amount of storage to allocate for your DB storage type in GiB (gibibytes).',
)
OPTIONAL_FIELD_ALLOCATED_STORAGE_GB_OPTIONAL = Field(
    None, description='The amount of storage to allocate for your DB storage type (in gibibytes).'
)
REQUIRED_FIELD_VPC_SECURITY_GROUP_IDS = Field(
    ..., description='A list of VPC security group IDs to associate with the DB.'
)

REQUIRED_FIELD_VPC_SUBNET_IDS = Field(
    ...,
    description='A list of VPC subnet IDs to associate with the DB. '
    'Provide at least two VPC subnet IDs in different Availability Zones when deploying with a Multi-AZ standby.',
)

OPTIONAL_FIELD_PUBLICLY_ACCESSIBLE = Field(
    True,
    description='Configures the DB with a public IP to facilitate access from outside the VPC.',
)

OPTIONAL_FIELD_USERNAME = Field(
    None, description='The username of the initial admin user created in InfluxDB.'
)
OPTIONAL_FIELD_ORGANIZATION = Field(
    None,
    description='The name of the initial organization for the initial admin user in InfluxDB.'
    'An InfluxDB organization is a workspace for a group of users',
)
REQUIRED_FIELD_BUCKET = Field(..., description='The name of the initial InfluxDB bucket.')
OPTIONAL_FIELD_BUCKET = Field(None, description='The name of the initial InfluxDB bucket.')
OPTIONAL_FIELD_DB_STORAGE_TYPE = Field(
    None,
    description='The Timestream for InfluxDB DB storage type to read and write InfluxDB data.',
)
OPTIONAL_FIELD_DEPLOYMENT_TYPE_INSTANCE = Field(
    None,
    description='Specifies whether the DB instance will be deployed as a standalone instance or with a Multi-AZ standby for high availability.',
)
OPTIONAL_FIELD_NETWORK_TYPE = Field(
    None,
    description='Specifies whether the network type of the Timestream for InfluxDB cluster is IPv4 or DUAL.',
)

OPTIONAL_FIELD_PORT = Field(
    None, description='The port number on which InfluxDB accepts connections. Default: 8086'
)
OPTIONAL_FIELD_PORT_UPDATE = Field(
    None, description='Update the DB cluster to use the specified port.'
)

OPTIONAL_FIELD_FAILOVER_MODE = Field(
    None,
    description='Specifies the behavior of failure recovery when the primary node of the cluster fails.',
)
OPTIONAL_FIELD_FAILOVER_MODE_UPDATE = Field(
    None, description="Update the DB cluster's failover behavior."
)

OPTIONAL_FIELD_TAGS = Field(None, description='A list of tags to assign to the DB.')
OPTIONAL_FIELD_TAGS_PARAM_GROUP = Field(
    None, description='A list of key-value pairs to associate with the DB parameter group.'
)
OPTIONAL_FIELD_LOG_DELIVERY_CONFIGURATION = Field(
    None, description='Configuration for sending InfluxDB engine logs to a specified S3 bucket.'
)
OPTIONAL_FIELD_LOG_DELIVERY_CONFIGURATION_UPDATE = Field(
    None, description='The log delivery configuration to apply to the DB cluster.'
)

# Pagination fields
OPTIONAL_FIELD_NEXT_TOKEN = Field(
    None,
    description='The pagination token. To resume pagination, provide the next-token value as an argument of a subsequent API invocation.',
)

OPTIONAL_FIELD_MAX_RESULTS = Field(
    None,
    description='The maximum number of items to return in the output. If the total number of items available is more than the value specified, a nextToken is provided in the output.',
)

# Resource fields
REQUIRED_FIELD_RESOURCE_ARN = Field(
    ..., description='The Amazon Resource Name (ARN) of the tagged resource.'
)
REQUIRED_FIELD_TAG_KEYS = Field(..., description='The keys used to identify the tags to remove.')
REQUIRED_FIELD_TAGS_RESOURCE = Field(..., description='A list of key-value pairs as tags.')

# DB Parameter Group fiels
REQUIRED_FIELD_PARAMETER_GROUP_ID = Field(..., description='The id of the DB parameter group.')
REQUIRED_FIELD_PARAM_GROUP_NAME = Field(
    ...,
    description='The name of the DB parameter group. The name must be unique per customer and per region.',
)
OPTIONAL_FIELD_PARAM_GROUP_DESCRIPTION = Field(
    None, description='A description of the DB parameter group.'
)
OPTIONAL_FIELD_PARAMETERS = Field(
    None, description='A list of the parameters that comprise the DB parameter group.'
)
OPTIONAL_FIELD_DB_PARAMETER_GROUP_ID = Field(
    None, description='The id of the DB parameter group to assign to your DB.'
)
OPTIONAL_FIELD_DB_PARAMETER_GROUP_IDENTIFIER_UPDATE = Field(
    None, description='Update the DB cluster to use the specified DB parameter group.'
)

# DB Instance fields
REQUIRED_FIELD_DB_INSTANCE_IDENTIFIER = Field(..., description='The id of the DB instance.')

# Status fields
REQUIRED_FIELD_STATUS = Field(
    ..., description='The status to filter DB instances by (case-insensitive).'
)
REQUIRED_FIELD_STATUS_CLUSTER = Field(
    ..., description='The status to filter DB clusters by (case-insensitive).'
)

# InfluxDB fields
REQUIRED_FIELD_URL = Field(..., description='The URL of the InfluxDB server.')
REQUIRED_FIELD_TOKEN = Field(..., description='The authentication token.')
REQUIRED_FIELD_BUCKET_INFLUX = Field(..., description='The destination bucket for writes.')
REQUIRED_FIELD_ORG = Field(..., description='The organization name.')
REQUIRED_FIELD_POINTS = Field(
    ...,
    description='List of data points to write. Each point should be a dictionary with measurement, tags, fields, and optional time.',
)
REQUIRED_FIELD_DATA_LINE_PROTOCOL = Field(
    ..., description='Data in InfluxDB Line Protocol format.'
)
OPTIONAL_FIELD_WRITE_PRECISION = Field(
    None,
    description='The precision for the unix timestamps within the body line-protocol. One of: ns, us, ms, s (default is ns).',
)
OPTIONAL_FIELD_SYNC_MODE = Field(
    'synchronous', description="The synchronization mode, either 'synchronous' or 'asynchronous'."
)
OPTIONAL_FIELD_VERIFY_SSL = Field(
    True, description='Whether to verify SSL with https connections.'
)
REQUIRED_FIELD_QUERY = Field(..., description='The Flux query string.')

# Cluster name field
REQUIRED_FIELD_CLUSTER_NAME = Field(
    ...,
    description='The name that uniquely identifies the DB cluster when interacting with '
    'the Amazon Timestream for InfluxDB API and CLI commands. '
    'This name will also be a prefix included in the endpoint.',
)

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

    Raises:
        ValueError: If the URL does not use HTTPS protocol or is not properly formatted.
    """
    try:
        parsed_url = urlparse(url)
        url_scheme = parsed_url.scheme
        if url_scheme != 'https' and url_scheme != 'http':
            raise ValueError('URL must use HTTP(S) protocol')
    except Exception as e:
        logger.error(f'Error parsing URL: {str(e)}')
        raise

    if not token:
        raise ValueError('Token must be provided')

    return InfluxDBClient(url=url, token=token, org=org, timeout=timeout, verify_ssl=verify_ssl)


@mcp.tool(name='CreateDbCluster')
async def create_db_cluster(
    name: str = REQUIRED_FIELD_CLUSTER_NAME,
    db_instance_type: str = REQUIRED_FIELD_DB_INSTANCE_TYPE,
    password: str = REQUIRED_FIELD_PASSWORD,
    allocated_storage_gb: int = REQUIRED_FIELD_ALLOCATED_STORAGE_GB,
    vpc_security_group_ids: List[str] = REQUIRED_FIELD_VPC_SECURITY_GROUP_IDS,
    vpc_subnet_ids: List[str] = REQUIRED_FIELD_VPC_SUBNET_IDS,
    publicly_accessible: bool = OPTIONAL_FIELD_PUBLICLY_ACCESSIBLE,
    username: Optional[str] = OPTIONAL_FIELD_USERNAME,
    organization: Optional[str] = OPTIONAL_FIELD_ORGANIZATION,
    bucket: Optional[str] = OPTIONAL_FIELD_BUCKET,
    db_storage_type: Optional[str] = OPTIONAL_FIELD_DB_STORAGE_TYPE,
    deployment_type: Optional[str] = OPTIONAL_FIELD_DEPLOYMENT_TYPE_INSTANCE,
    networkType: Optional[str] = OPTIONAL_FIELD_NETWORK_TYPE,
    port: Optional[int] = OPTIONAL_FIELD_PORT,
    db_parameter_group_identifier: Optional[str] = OPTIONAL_FIELD_DB_PARAMETER_GROUP_ID,
    failover_mode: Optional[str] = OPTIONAL_FIELD_FAILOVER_MODE,
    tags: Optional[Dict[str, str]] = OPTIONAL_FIELD_TAGS,
    log_delivery_configuration: Optional[
        Dict[str, Any]
    ] = OPTIONAL_FIELD_LOG_DELIVERY_CONFIGURATION,
) -> Dict[str, Any]:
    """Create a new Timestream for InfluxDB database cluster.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_CreateDbCluster.html

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
    db_instance_name: str = REQUIRED_FIELD_DB_INSTANCE_NAME,
    db_instance_type: str = REQUIRED_FIELD_DB_INSTANCE_TYPE,
    password: str = REQUIRED_FIELD_PASSWORD,
    allocated_storage_gb: int = REQUIRED_FIELD_ALLOCATED_STORAGE_GB,
    vpc_security_group_ids: List[str] = REQUIRED_FIELD_VPC_SECURITY_GROUP_IDS,
    vpc_subnet_ids: List[str] = REQUIRED_FIELD_VPC_SUBNET_IDS,
    publicly_accessible: bool = OPTIONAL_FIELD_PUBLICLY_ACCESSIBLE,
    username: Optional[str] = OPTIONAL_FIELD_USERNAME,
    organization: Optional[str] = OPTIONAL_FIELD_ORGANIZATION,
    bucket: Optional[str] = OPTIONAL_FIELD_BUCKET,
    db_storage_type: Optional[str] = OPTIONAL_FIELD_DB_STORAGE_TYPE,
    deployment_type: Optional[str] = OPTIONAL_FIELD_DEPLOYMENT_TYPE_INSTANCE,
    networkType: Optional[str] = OPTIONAL_FIELD_NETWORK_TYPE,
    port: Optional[int] = OPTIONAL_FIELD_PORT,
    db_parameter_group_id: Optional[str] = OPTIONAL_FIELD_DB_PARAMETER_GROUP_ID,
    tags: Optional[Dict[str, str]] = OPTIONAL_FIELD_TAGS,
) -> Dict[str, Any]:
    """Create a new Timestream for InfluxDB database instance.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_CreateDbInstance.html#tsinfluxdb-CreateDbInstance-request-dbStorageType

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
    db_cluster_id: str = REQUIRED_FIELD_DB_CLUSTER_ID,
    next_token: Optional[str] = OPTIONAL_FIELD_NEXT_TOKEN,
    max_results: Optional[int] = OPTIONAL_FIELD_MAX_RESULTS,
) -> Dict[str, Any]:
    """Returns a list of Timestream for InfluxDB DB instances belonging to a specific cluster.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_ListDbInstancesForCluster.html

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
    next_token: Optional[str] = OPTIONAL_FIELD_NEXT_TOKEN,
    max_results: Optional[int] = OPTIONAL_FIELD_MAX_RESULTS,
) -> Dict[str, Any]:
    """Returns a list of Timestream for InfluxDB DB instances.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_ListDbInstances.html

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
    next_token: Optional[str] = OPTIONAL_FIELD_NEXT_TOKEN,
    max_results: Optional[int] = OPTIONAL_FIELD_MAX_RESULTS,
) -> Dict[str, Any]:
    """Returns a list of Timestream for InfluxDB DB clusters.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_ListDbClusters.html

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
async def get_db_parameter_group(
    identifier: str = REQUIRED_FIELD_PARAMETER_GROUP_ID,
) -> Dict[str, Any]:
    """Returns a Timestream for InfluxDB DB parameter group.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_GetDbParameterGroup.html

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
async def get_db_instance(
    identifier: str = REQUIRED_FIELD_DB_INSTANCE_IDENTIFIER,
) -> Dict[str, Any]:
    """Returns a Timestream for InfluxDB DB instance.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_GetDbInstance.html

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
async def get_db_cluster(
    db_cluster_id: str = REQUIRED_FIELD_DB_CLUSTER_ID,
) -> Dict[str, Any]:
    """Retrieves information about a Timestream for InfluxDB cluster.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_GetDbCluster.html

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
async def delete_db_instance(
    identifier: str = REQUIRED_FIELD_DB_INSTANCE_IDENTIFIER,
) -> Dict[str, Any]:
    """Deletes a Timestream for InfluxDB DB instance.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_DeleteDbInstance.html

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
async def delete_db_cluster(
    db_cluster_id: str = REQUIRED_FIELD_DB_CLUSTER_ID,
) -> Dict[str, Any]:
    """Deletes a Timestream for InfluxDB cluster.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_DeleteDbCluster.html

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
    next_token: Optional[str] = OPTIONAL_FIELD_NEXT_TOKEN,
    max_results: Optional[int] = OPTIONAL_FIELD_MAX_RESULTS,
) -> Dict[str, Any]:
    """Returns a list of Timestream for InfluxDB DB parameter groups.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_ListDbParameterGroups.html

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
async def list_tags_for_resource(
    resource_arn: str = REQUIRED_FIELD_RESOURCE_ARN,
) -> Dict[str, Any]:
    """A list of tags applied to the resource.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_ListTagsForResource.html

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
async def tag_resource(
    resource_arn: str = REQUIRED_FIELD_RESOURCE_ARN,
    tags: Dict[str, str] = REQUIRED_FIELD_TAGS_RESOURCE,
) -> Dict[str, Any]:
    """Tags are composed of a Key/Value pairs. You can use tags to categorize and track your Timestream for InfluxDB resources.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_TagResource.html

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
async def untag_resource(
    resource_arn: str = REQUIRED_FIELD_RESOURCE_ARN,
    tag_keys: List[str] = REQUIRED_FIELD_TAG_KEYS,
) -> Dict[str, Any]:
    """Removes the tag from the specified resource.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_UntagResource.html

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
    db_cluster_id: str = REQUIRED_FIELD_DB_CLUSTER_ID,
    db_instance_type: Optional[str] = OPTIONAL_FIELD_DB_INSTANCE_TYPE_CLUSTER_UPDATE,
    db_parameter_group_identifier: Optional[
        str
    ] = OPTIONAL_FIELD_DB_PARAMETER_GROUP_IDENTIFIER_UPDATE,
    port: Optional[int] = OPTIONAL_FIELD_PORT_UPDATE,
    failover_mode: Optional[str] = OPTIONAL_FIELD_FAILOVER_MODE_UPDATE,
    log_delivery_configuration: Optional[
        Dict[str, Any]
    ] = OPTIONAL_FIELD_LOG_DELIVERY_CONFIGURATION_UPDATE,
) -> Dict[str, Any]:
    """Updates a Timestream for InfluxDB cluster.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_UpdateDbCluster.html

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
    identifier: str = REQUIRED_FIELD_DB_INSTANCE_IDENTIFIER,
    db_instance_type: Optional[str] = OPTIONAL_FIELD_DB_INSTANCE_TYPE_CLUSTER_UPDATE,
    db_parameter_group_identifier: Optional[str] = OPTIONAL_FIELD_DB_PARAMETER_GROUP_ID,
    port: Optional[int] = OPTIONAL_FIELD_PORT,
    allocated_storage_gb: Optional[int] = OPTIONAL_FIELD_ALLOCATED_STORAGE_GB_OPTIONAL,
    db_storage_type: Optional[str] = OPTIONAL_FIELD_DB_STORAGE_TYPE,
    deployment_type: Optional[str] = OPTIONAL_FIELD_DEPLOYMENT_TYPE_INSTANCE,
    log_delivery_configuration: Optional[
        Dict[str, Any]
    ] = OPTIONAL_FIELD_LOG_DELIVERY_CONFIGURATION,
) -> Dict[str, Any]:
    """Updates a Timestream for InfluxDB DB instance.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_UpdateDbInstance.html

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
async def list_db_instances_by_status(
    status: str = REQUIRED_FIELD_STATUS,
) -> Dict[str, Any]:
    """Returns a list of Timestream for InfluxDB DB instances filtered by status.

    This tool paginates through all DB instances and filters them by the provided status
    in a case-insensitive manner.

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
async def list_db_clusters_by_status(
    status: str = REQUIRED_FIELD_STATUS_CLUSTER,
) -> Dict[str, Any]:
    """Returns a list of Timestream for InfluxDB DB clusters filtered by status.

    This tool paginates through all DB clusters and filters them by the provided status
    in a case-insensitive manner.

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
    name: str = REQUIRED_FIELD_PARAM_GROUP_NAME,
    description: Optional[str] = OPTIONAL_FIELD_PARAM_GROUP_DESCRIPTION,
    parameters: Optional[Dict[str, Any]] = OPTIONAL_FIELD_PARAMETERS,
    tags: Optional[Dict[str, str]] = OPTIONAL_FIELD_TAGS,
) -> Dict[str, Any]:
    """Creates a new Timestream for InfluxDB DB parameter group to associate with DB instances.

    API reference: https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_CreateDbParameterGroup.html

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
    url: str = REQUIRED_FIELD_URL,
    token: str = REQUIRED_FIELD_TOKEN,
    bucket: str = REQUIRED_FIELD_BUCKET,
    org: str = REQUIRED_FIELD_ORG,
    points: List[Dict[str, Any]] = REQUIRED_FIELD_POINTS,
    write_precision: Optional[str] = OPTIONAL_FIELD_WRITE_PRECISION,
    sync_mode: str = OPTIONAL_FIELD_SYNC_MODE,
    verify_ssl: bool = OPTIONAL_FIELD_VERIFY_SSL,
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
    url: str = REQUIRED_FIELD_URL,
    token: str = REQUIRED_FIELD_TOKEN,
    bucket: str = REQUIRED_FIELD_BUCKET,
    org: str = REQUIRED_FIELD_ORG,
    data_line_protocol: str = REQUIRED_FIELD_DATA_LINE_PROTOCOL,
    write_precision: Optional[str] = OPTIONAL_FIELD_WRITE_PRECISION,
    sync_mode: str = OPTIONAL_FIELD_SYNC_MODE,
    verify_ssl: bool = OPTIONAL_FIELD_VERIFY_SSL,
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
    url: str = REQUIRED_FIELD_URL,
    token: str = REQUIRED_FIELD_TOKEN,
    org: str = REQUIRED_FIELD_ORG,
    query: str = REQUIRED_FIELD_QUERY,
    verify_ssl: bool = OPTIONAL_FIELD_VERIFY_SSL,
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
