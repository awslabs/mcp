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
"""Cluster Information API Module.

This module provides functions to retrieve information about MSK clusters.
"""

import boto3
from .describe_cluster import describe_cluster
from .describe_cluster_operation import describe_cluster_operation
from .get_bootstrap_brokers import get_bootstrap_brokers
from .get_cluster_policy import get_cluster_policy
from .get_compatible_kafka_versions import get_compatible_kafka_versions
from .list_client_vpc_connections import list_client_vpc_connections
from .list_cluster_operations import list_cluster_operations
from .list_nodes import list_nodes
from .list_scram_secrets import list_scram_secrets
from awslabs.aws_msk_mcp_server import __version__
from botocore.config import Config
from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register_module(mcp: FastMCP) -> None:
    """Registers this tool with the mcp."""

    @mcp.tool(
        name='describe_cluster_operation',
        description="""Returns detailed information about a specific MSK cluster operation.

Related Resources:
- resource://msk-documentation/developer-guide - Full MSK Developer Guide with information on cluster operations

This operation retrieves detailed information about a specific cluster operation, including its type, state, and progress.

=== INPUT PARAMETERS ===

- cluster_operation_arn (str): The Amazon Resource Name (ARN) of the cluster operation to describe.
- region (str): AWS region where the cluster operation is located.

=== OUTPUT (JSON) ===

{
    "ClusterOperationInfo": {
        "ClusterArn": "arn:aws:kafka:us-west-2:123456789012:cluster/cluster-name/abcd1234-abcd-1234-abcd-1234abcd1234",
        "ClusterOperationArn": "arn:aws:kafka:us-west-2:123456789012:cluster-operation/operation-id",
        "OperationType": "UPDATE_BROKER_STORAGE",
        "SourceClusterInfo": {
            "KafkaVersion": "2.8.1",
            "ConfigurationInfo": {
                "Arn": "arn:aws:kafka:us-west-2:123456789012:configuration/configuration-name/abcd1234",
                "Revision": 1
            }
        },
        "TargetClusterInfo": {
            "KafkaVersion": "2.8.1",
            "ConfigurationInfo": {
                "Arn": "arn:aws:kafka:us-west-2:123456789012:configuration/configuration-name/abcd1234",
                "Revision": 2
            }
        },
        "OperationSteps": [
            {
                "StepName": "UPDATING_CLUSTER",
                "StepStatus": "COMPLETED"
            }
        ],
        "OperationState": "COMPLETED",
        "CreationTime": "2023-01-01T12:00:00.000Z",
        "EndTime": "2023-01-01T12:30:00.000Z"
    }
}

=== NOTES ===

- Cluster operations represent asynchronous actions like cluster creation, updates, or deletions.
- The OperationState field indicates the current status (PENDING, IN_PROGRESS, COMPLETED, FAILED).
- If the operation failed, the ErrorInfo field will contain details about the failure.
- The OperationSteps field provides a breakdown of the individual steps in the operation.""",
    )
    def describe_cluster_operation_tool(
        region: str = Field(..., description='AWS region'),
        cluster_operation_arn: str = Field(
            ..., description='The Amazon Resource Name (ARN) of the cluster operation'
        ),
    ):
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )
        return describe_cluster_operation(cluster_operation_arn, client)

    @mcp.tool(
        name='get_cluster_info',
        description=r"""Unified API to retrieve various types of information about MSK clusters.

This operation provides a comprehensive view of an MSK cluster by retrieving multiple types of information in a single call.

=== ACTION MODES ===

1. info_type = "metadata"
- Retrieves basic cluster metadata including name, state, and version.

Required parameters:
- cluster_arn (str): The ARN of the cluster
- region (str): AWS region

Output (JSON):
{
    "ClusterInfo": {
        "ClusterArn": "arn:aws:kafka:us-west-2:123456789012:cluster/cluster-name/abcd1234",
        "ClusterName": "cluster-name",
        "State": "ACTIVE",
        "CreationTime": "2023-01-01T12:00:00.000Z",
        "CurrentVersion": "K3AEGXETSR30VB"
    }
}

2. info_type = "brokers"
- Retrieves bootstrap broker connection strings for the cluster.

Required parameters:
- cluster_arn (str): The ARN of the cluster
- region (str): AWS region

Output (JSON):
{
    "BootstrapBrokerString": "b-1.cluster-name.abcd1234.c2.kafka.us-west-2.amazonaws.com:9092,b-2.cluster-name.abcd1234.c2.kafka.us-west-2.amazonaws.com:9092",
    "BootstrapBrokerStringTls": "b-1.cluster-name.abcd1234.c2.kafka.us-west-2.amazonaws.com:9094,b-2.cluster-name.abcd1234.c2.kafka.us-west-2.amazonaws.com:9094"
}

3. info_type = "nodes"
- Retrieves information about the broker nodes in the cluster.

Required parameters:
- cluster_arn (str): The ARN of the cluster
- region (str): AWS region

Output (JSON):
{
    "NodeInfoList": [
        {
            "BrokerNodeInfo": {
                "BrokerId": 1,
                "ClientSubnet": "subnet-1234abcd",
                "ClientVpcIpAddress": "172.31.1.1",
                "CurrentBrokerSoftwareInfo": {
                    "KafkaVersion": "2.8.1"
                }
            }
        }
    ]
}

4. info_type = "compatible_versions"
- Retrieves Kafka versions that the cluster can be upgraded to.

Required parameters:
- cluster_arn (str): The ARN of the cluster
- region (str): AWS region

Output (JSON):
{
    "CompatibleKafkaVersions": [
        {
            "SourceVersion": "2.8.1",
            "TargetVersions": ["3.3.1"]
        }
    ]
}

5. info_type = "policy"
- Retrieves the resource policy attached to the cluster.

Required parameters:
- cluster_arn (str): The ARN of the cluster
- region (str): AWS region

Output (JSON):
{
    "CurrentVersion": "1",
    "Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[...]}"
}

6. info_type = "operations"
- Retrieves the history of operations performed on the cluster.

Required parameters:
- cluster_arn (str): The ARN of the cluster
- region (str): AWS region

Optional parameters:
- max_results (int): Maximum number of operations to return (default: 10)
- next_token (str): Token for pagination

Output (JSON):
{
    "ClusterOperationInfoList": [
        {
            "ClusterOperationArn": "arn:aws:kafka:us-west-2:123456789012:cluster-operation/operation-id",
            "OperationType": "UPDATE_BROKER_STORAGE",
            "OperationState": "COMPLETED"
        }
    ],
    "NextToken": "AAAABBBCCC"
}

7. info_type = "client_vpc_connections"
- Retrieves VPC connections associated with the cluster.

Required parameters:
- cluster_arn (str): The ARN of the cluster
- region (str): AWS region

Optional parameters:
- max_results (int): Maximum number of connections to return (default: 10)
- next_token (str): Token for pagination

Output (JSON):
{
    "VpcConnectionInfoList": [
        {
            "VpcConnectionArn": "arn:aws:kafka:us-west-2:123456789012:vpc-connection/connection-id",
            "VpcConnectionState": "ACTIVE"
        }
    ],
    "NextToken": "AAAABBBCCC"
}

8. info_type = "scram_secrets"
- Retrieves SCRAM secrets associated with the cluster.

Required parameters:
- cluster_arn (str): The ARN of the cluster
- region (str): AWS region

Optional parameters:
- max_results (int): Maximum number of secrets to return
- next_token (str): Token for pagination

Output (JSON):
{
    "SecretArnList": [
        "arn:aws:secretsmanager:us-west-2:123456789012:secret:secret-name"
    ],
    "NextToken": "AAAABBBCCC"
}

9. info_type = "all"
- Retrieves all of the above information in a single call.

Required parameters:
- cluster_arn (str): The ARN of the cluster
- region (str): AWS region

Output (JSON):
{
    "metadata": { /* metadata response */ },
    "brokers": { /* brokers response */ },
    "nodes": { /* nodes response */ },
    "compatible_versions": { /* compatible_versions response */ },
    "policy": { /* policy response */ },
    "operations": { /* operations response */ },
    "client_vpc_connections": { /* client_vpc_connections response */ },
    "scram_secrets": { /* scram_secrets response */ }
}

=== NOTES ===

- This tool provides a convenient way to get comprehensive information about a cluster in a single call.
- When info_type is "all", any errors in retrieving specific components will be included in the response.
- For large clusters with many operations or connections, use pagination parameters in kwargs.
- The response structure varies based on the info_type requested.""",
    )
    def get_cluster_info(
        region: str = Field(..., description='AWS region'),
        cluster_arn: str = Field(..., description='The ARN of the cluster to get information for'),
        info_type: str = Field(
            'all',
            description='Type of information to retrieve (metadata, brokers, nodes, compatible_versions, policy, operations, client_vpc_connections, scram_secrets, all)',
        ),
        kwargs: dict = Field({}, description='Additional arguments specific to each info type'),
    ):
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
