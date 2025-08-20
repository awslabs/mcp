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
"""
Cluster Information API Module

This module provides functions to retrieve information about MSK clusters.
"""

import boto3
from botocore.config import Config
from awslabs.aws_msk_mcp_server import __version__
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .describe_cluster import describe_cluster
from .describe_cluster_operation import describe_cluster_operation
from .get_bootstrap_brokers import get_bootstrap_brokers
from .get_cluster_policy import get_cluster_policy
from .get_compatible_kafka_versions import get_compatible_kafka_versions
from .list_client_vpc_connections import list_client_vpc_connections
from .list_cluster_operations import list_cluster_operations
from .list_nodes import list_nodes
from .list_scram_secrets import list_scram_secrets


def register_module(mcp: FastMCP) -> None:
    @mcp.tool(name='describe_cluster_operation')
    def describe_cluster_operation_tool(
        region: str = Field(..., description='AWS region'),
        cluster_operation_arn: str = Field(
            ..., description='The Amazon Resource Name (ARN) of the cluster operation'
        ),
    ):
        """
        Returns information about a cluster operation.

        Args:
            cluster_operation_arn (str): The Amazon Resource Name (ARN) of the cluster operation
            region (str): AWS region

        Returns:
            dict: Information about the cluster operation containing:
                - ClusterOperationInfo (dict): Detailed information about the operation including:
                    - ClusterArn (str): The ARN of the cluster this operation is performed on
                    - ClusterOperationArn (str): The ARN of the cluster operation
                    - OperationType (str): The type of operation (e.g., UPDATE, CREATE, DELETE)
                    - SourceClusterInfo (dict, optional): Information about the source cluster
                    - TargetClusterInfo (dict, optional): Information about the target cluster configuration
                    - OperationSteps (list, optional): List of steps in the operation
                    - OperationState (str): The state of the operation (e.g., PENDING, IN_PROGRESS, COMPLETED)
                    - ErrorInfo (dict, optional): Information about any errors that occurred
                    - CreationTime (datetime): The time when the operation was created
                    - EndTime (datetime, optional): The time when the operation completed
        """
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )
        return describe_cluster_operation(cluster_operation_arn, client)

    @mcp.tool(name='get_cluster_info')
    def get_cluster_info(
        region: str = Field(..., description='AWS region'),
        cluster_arn: str = Field(..., description='The ARN of the cluster to get information for'),
        info_type: str = Field(
            'all',
            description='Type of information to retrieve (metadata, brokers, nodes, compatible_versions, policy, operations, client_vpc_connections, scram_secrets, all)',
        ),
        kwargs: dict = Field({}, description='Additional arguments specific to each info type'),
    ):
        """
        Unified API to retrieve various types of information about MSK clusters.

        Args:
            cluster_arn (str): The ARN of the cluster to get information for
            info_type (str): Type of information to retrieve (metadata, brokers, nodes, compatible_versions,
                            policy, operations, client_vpc_connections, scram_secrets, all)
            region (str): AWS region
            kwargs (dict, optional): Additional arguments specific to each info type:
                      - For "operations":
                          - max_results (int, optional): Maximum number of operations to return (default: 10)
                          - next_token (str, optional): Token for pagination
                      - For "client_vpc_connections":
                          - max_results (int, optional): Maximum number of connections to return (default: 10)
                          - next_token (str, optional): Token for pagination
                      - For "scram_secrets":
                          - max_results (int, optional): Maximum number of secrets to return
                          - next_token (str, optional): Token for pagination

        Returns:
            dict: Cluster information of the requested type, or a dictionary containing all types if info_type is "all":
                - metadata (dict): Cluster metadata from describe_cluster
                - brokers (dict): Bootstrap broker information from get_bootstrap_brokers
                - nodes (dict): Node information from list_nodes
                - compatible_versions (dict): Compatible Kafka versions from get_compatible_kafka_versions
                - policy (dict): Cluster policy information from get_cluster_policy
                - operations (dict): Cluster operations from list_cluster_operations
                - client_vpc_connections (dict): Client VPC connections from list_client_vpc_connections
                - scram_secrets (dict): SCRAM secrets from list_scram_secrets

                Each of these keys contains the full response structure as documented in their respective functions.
                If an error occurs while retrieving any of these components, the corresponding key will contain
                an error message instead of the expected data structure.
        """

        # Create a single boto3 client to be shared across all function calls
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )

        if info_type == 'all':
            # Retrieve all types of information for the cluster
            result = {}

            # Use try-except blocks for each function call to handle potential errors
            try:
                result['metadata'] = describe_cluster(cluster_arn, client)
            except Exception as e:
                result['metadata'] = {'error': str(e)}

            try:
                result['brokers'] = get_bootstrap_brokers(cluster_arn, client)
            except Exception as e:
                result['brokers'] = {'error': str(e)}

            try:
                result['nodes'] = list_nodes(cluster_arn, client)
            except Exception as e:
                result['nodes'] = {'error': str(e)}

            try:
                result['compatible_versions'] = get_compatible_kafka_versions(cluster_arn, client)
            except Exception as e:
                result['compatible_versions'] = {'error': str(e)}

            try:
                result['policy'] = get_cluster_policy(cluster_arn, client)
            except Exception as e:
                result['policy'] = {'error': str(e)}

            try:
                result['operations'] = list_cluster_operations(cluster_arn, client)
            except Exception as e:
                result['operations'] = {'error': str(e)}

            try:
                result['client_vpc_connections'] = list_client_vpc_connections(cluster_arn, client)
            except Exception as e:
                result['client_vpc_connections'] = {'error': str(e)}

            try:
                result['scram_secrets'] = list_scram_secrets(cluster_arn, client)
            except Exception as e:
                result['scram_secrets'] = {'error': str(e)}

            return result
        elif info_type == 'metadata':
            return describe_cluster(cluster_arn, client)
        elif info_type == 'brokers':
            return get_bootstrap_brokers(cluster_arn, client)
        elif info_type == 'nodes':
            return list_nodes(cluster_arn, client)
        elif info_type == 'compatible_versions':
            return get_compatible_kafka_versions(cluster_arn, client)
        elif info_type == 'policy':
            return get_cluster_policy(cluster_arn, client)
        elif info_type == 'operations':
            # Extract only the parameters that list_cluster_operations accepts
            max_results = kwargs.get('max_results', 10)
            next_token = kwargs.get('next_token', None)
            return list_cluster_operations(cluster_arn, client, max_results, next_token)
        elif info_type == 'client_vpc_connections':
            # Extract only the parameters that list_client_vpc_connections accepts
            max_results = kwargs.get('max_results', 10)
            next_token = kwargs.get('next_token', None)
            return list_client_vpc_connections(cluster_arn, client, max_results, next_token)
        elif info_type == 'scram_secrets':
            # Extract only the parameters that list_scram_secrets accepts
            max_results = kwargs.get('max_results', None)
            next_token = kwargs.get('next_token', None)
            return list_scram_secrets(cluster_arn, client, max_results, next_token)
        else:
            raise ValueError(f'Unsupported info_type: {info_type}')
