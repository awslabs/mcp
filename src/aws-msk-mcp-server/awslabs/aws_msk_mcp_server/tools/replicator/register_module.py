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

"""Replicator API Module.

This module provides functions to manage MSK replicators.
"""

import boto3
from .create_replicator import create_replicator
from .describe_replicator import describe_replicator
from .list_replicators import list_replicators
from awslabs.aws_msk_mcp_server import __version__
from botocore.config import Config
from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register_module(mcp: FastMCP) -> None:
    """Registers this tool with the mcp."""

    @mcp.tool(
        name='describe_replicator',
        description="""Get detailed information about an MSK replicator

This operation retrieves detailed information about a specific MSK replicator, including its configuration, state, and replication settings.

=== INPUT PARAMETERS ===

- replicator_arn (str): The Amazon Resource Name (ARN) of the replicator to describe.
- region (str): AWS region where the replicator is located.

=== OUTPUT (JSON) ===

{
    "ReplicatorInfo": {
        "ReplicatorArn": "arn:aws:kafka:us-west-2:123456789012:replicator/my-replicator/abcd1234",
        "ReplicatorName": "my-replicator",
        "KafkaClusters": [
            {
                "AmazonMskCluster": {
                    "MskClusterArn": "arn:aws:kafka:us-west-2:123456789012:cluster/source-cluster/abcd1234"
                },
                "VpcConfig": {
                    "SecurityGroupIds": ["sg-abcd1234"],
                    "SubnetIds": ["subnet-abcd1234", "subnet-efgh5678"]
                }
            },
            {
                "AmazonMskCluster": {
                    "MskClusterArn": "arn:aws:kafka:us-west-2:123456789012:cluster/target-cluster/efgh5678"
                },
                "VpcConfig": {
                    "SecurityGroupIds": ["sg-efgh5678"],
                    "SubnetIds": ["subnet-1234abcd", "subnet-5678efgh"]
                }
            }
        ],
        "ReplicationInfoList": [
            {
                "ConsumerGroupReplication": {
                    "ConsumerGroupsToExclude": ["exclude-group"],
                    "DetectAndCopyNewConsumerGroups": true
                },
                "SourceKafkaClusterArn": "arn:aws:kafka:us-west-2:123456789012:cluster/source-cluster/abcd1234",
                "TargetKafkaClusterArn": "arn:aws:kafka:us-west-2:123456789012:cluster/target-cluster/efgh5678",
                "TopicReplication": {
                    "CopyAccessControlListsForTopics": true,
                    "CopyTopicConfigurations": true,
                    "DetectAndCopyNewTopics": true,
                    "TopicsToExclude": ["exclude-topic"]
                }
            }
        ],
        "ServiceExecutionRoleArn": "arn:aws:iam::123456789012:role/MSKReplicatorRole",
        "ReplicatorState": "RUNNING",
        "CreationTime": "2023-01-01T12:00:00.000Z",
        "CurrentVersion": "1.0.0",
        "Tags": {
            "Environment": "Production"
        }
    }
}

=== NOTES ===

- MSK replicators enable cross-region or cross-cluster replication of Kafka topics.
- The ReplicatorState field indicates the current status (CREATING, RUNNING, UPDATING, DELETING, FAILED).
- The KafkaClusters array contains information about both source and target clusters.
- The ReplicationInfoList contains details about which topics and consumer groups are being replicated.""",
    )
    def describe_replicator_tool(
        region: str = Field(..., description='AWS region'),
        replicator_arn: str = Field(
            ..., description='The Amazon Resource Name (ARN) of the replicator'
        ),
    ):
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )
        return describe_replicator(replicator_arn, client)

    @mcp.tool(
        name='create_replicator',
        description="""Create a new MSK replicator for cross-cluster data replication

This operation creates a new replicator to copy data between two MSK clusters, enabling cross-region or cross-cluster replication.

=== INPUT PARAMETERS ===

- replicator_name (str): The name of the replicator.
- source_kafka_cluster_arn (str): The ARN of the source Kafka cluster.
- target_kafka_cluster_arn (str): The ARN of the target Kafka cluster.
- service_execution_role_arn (str): The ARN of the IAM role used by the replicator.
- region (str): AWS region where the replicator will be created.
- kafka_clusters (dict, optional): Configuration details for the source and target clusters. Example:
    {
        "KafkaClusters": [
            {
                "AmazonMskCluster": {
                    "MskClusterArn": "arn:aws:kafka:us-west-2:123456789012:cluster/source-cluster/abcd1234"
                },
                "VpcConfig": {
                    "SecurityGroupIds": ["sg-abcd1234"],
                    "SubnetIds": ["subnet-abcd1234", "subnet-efgh5678"]
                }
            },
            {
                "AmazonMskCluster": {
                    "MskClusterArn": "arn:aws:kafka:us-west-2:123456789012:cluster/target-cluster/efgh5678"
                },
                "VpcConfig": {
                    "SecurityGroupIds": ["sg-efgh5678"],
                    "SubnetIds": ["subnet-1234abcd", "subnet-5678efgh"]
                }
            }
        ]
    }
- replication_info_list (list, optional): List of topic configurations to replicate. Example:
    [
        {
            "SourceKafkaClusterArn": "arn:aws:kafka:us-west-2:123456789012:cluster/source-cluster/abcd1234",
            "TargetKafkaClusterArn": "arn:aws:kafka:us-west-2:123456789012:cluster/target-cluster/efgh5678",
            "TopicReplication": {
                "CopyAccessControlListsForTopics": true,
                "CopyTopicConfigurations": true,
                "DetectAndCopyNewTopics": true,
                "TopicsToExclude": ["exclude-topic"]
            },
            "ConsumerGroupReplication": {
                "ConsumerGroupsToExclude": ["exclude-group"],
                "DetectAndCopyNewConsumerGroups": true
            }
        }
    ]
- tags (dict, optional): Key-value pairs to associate with the replicator. Example:
    {
        "Environment": "Production",
        "Owner": "DataTeam"
    }

=== OUTPUT (JSON) ===

{
    "ReplicatorArn": "arn:aws:kafka:us-west-2:123456789012:replicator/my-replicator/abcd1234",
    "ReplicatorName": "my-replicator",
    "ReplicatorState": "CREATING",
    "CreationTime": "2023-01-01T12:00:00.000Z",
    "Tags": {
        "Environment": "Production",
        "Owner": "DataTeam"
    }
}

=== NOTES ===

- The replicator creation process is asynchronous; the initial state will be CREATING.
- The service execution role must have permissions to read from the source cluster and write to the target cluster.
- You can configure which topics and consumer groups to replicate or exclude.
- Replication can be configured to automatically detect and copy new topics and consumer groups.""",
    )
    def create_replicator_tool(
        region: str = Field(..., description='AWS region'),
        replicator_name: str = Field(..., description='The name of the replicator'),
        source_kafka_cluster_arn: str = Field(
            ..., description='The ARN of the source Kafka cluster'
        ),
        target_kafka_cluster_arn: str = Field(
            ..., description='The ARN of the target Kafka cluster'
        ),
        service_execution_role_arn: str = Field(
            ..., description='The ARN of the IAM role used by the replicator'
        ),
        kafka_clusters: dict = Field(
            None, description='Configuration details for the source and target clusters'
        ),
        replication_info_list: list = Field(
            None, description='List of topic configurations to replicate'
        ),
        tags: dict = Field(None, description='Key-value pairs to associate with the replicator'),
    ):
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )
        return create_replicator(
            replicator_name,
            source_kafka_cluster_arn,
            target_kafka_cluster_arn,
            service_execution_role_arn,
            client,
            kafka_clusters,
            replication_info_list,
            tags,
        )

    @mcp.tool(
        name='list_replicators',
        description="""List all MSK replicators in the specified AWS region

This operation retrieves a list of all MSK replicators in the specified AWS region.

=== INPUT PARAMETERS ===

- region (str): AWS region where to list replicators.
- max_results (int, optional): Maximum number of replicators to return in a single call.
- next_token (str, optional): Token for pagination to retrieve the next set of results.

=== OUTPUT (JSON) ===

{
    "ReplicatorInfoList": [
        {
            "ReplicatorArn": "arn:aws:kafka:us-west-2:123456789012:replicator/replicator-1/abcd1234",
            "ReplicatorName": "replicator-1",
            "ReplicatorState": "RUNNING",
            "CreationTime": "2023-01-01T12:00:00.000Z"
        },
        {
            "ReplicatorArn": "arn:aws:kafka:us-west-2:123456789012:replicator/replicator-2/efgh5678",
            "ReplicatorName": "replicator-2",
            "ReplicatorState": "CREATING",
            "CreationTime": "2023-01-02T12:00:00.000Z"
        }
    ],
    "NextToken": "AAAABBBCCC"
}

=== NOTES ===

- This operation returns a summary of each replicator; use describe_replicator to get detailed information.
- The NextToken field is only present when there are more results available.
- For accounts with many replicators, use pagination parameters to retrieve all results.
- The ReplicatorState field indicates the current status of each replicator.""",
    )
    def list_replicators_tool(
        region: str = Field(..., description='AWS region'),
        max_results: int = Field(None, description='Maximum number of replicators to return'),
        next_token: str = Field(None, description='Token for pagination'),
    ):
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )
        return list_replicators(client, max_results, next_token)
