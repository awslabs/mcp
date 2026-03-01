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
Topics Information API Module

This module provides functions to retrieve information about topics in MSK clusters.
"""

from typing import Optional

import boto3
from botocore.config import Config
from awslabs.aws_msk_mcp_server import __version__
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .describe_topic import describe_topic
from .describe_topic_partitions import describe_topic_partitions
from .list_topics import list_topics


def register_module(mcp: FastMCP) -> None:
    @mcp.tool(name='list_topics', description='Returns all topics in an MSK cluster.')
    def list_topics_tool(
        region: str = Field(..., description='AWS region'),
        cluster_arn: str = Field(
            ..., description='The Amazon Resource Name (ARN) that uniquely identifies the cluster'
        ),
        topic_name_filter: Optional[str] = Field(
            None, description='Returns topics starting with given name'
        ),
        max_results: Optional[int] = Field(
            None,
            description='The maximum number of results to return in the response (default maximum 100 results per API call)',
        ),
        next_token: Optional[str] = Field(
            None,
            description='The paginated results marker. When the result of the operation is truncated, the call returns NextToken in the response',
        ),
    ):
        """
        Returns all topics in an MSK cluster.

        Args:
            region (str): AWS region
            cluster_arn (str): The Amazon Resource Name (ARN) that uniquely identifies the cluster
            topic_name_filter (str, optional): Returns topics starting with given name
            max_results (int, optional): The maximum number of results to return in the response
                                       (default maximum 100 results per API call)
            next_token (str, optional): The paginated results marker. When the result of the operation
                                      is truncated, the call returns NextToken in the response

        Returns:
            dict: Response containing:
                - topics (list): List of topic objects containing:
                    - topicArn (str): ARN of the topic
                    - topicName (str): Name of the topic
                    - partitionCount (int): Number of partitions in the topic
                    - replicationFactor (int): Replication factor for the topic
                    - outOfSyncReplicaCount (int): Number of out-of-sync replicas
                - nextToken (str, optional): The token for the next set of results, if there are more results
        """
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )

        # Build kwargs conditionally to avoid passing None values
        kwargs = {}
        if topic_name_filter is not None:
            kwargs['topic_name_filter'] = topic_name_filter
        if max_results is not None:
            kwargs['max_results'] = max_results
        if next_token is not None:
            kwargs['next_token'] = next_token

        return list_topics(cluster_arn, client, **kwargs)

    @mcp.tool(
        name='describe_topic',
        description='Returns details for a specific topic on an MSK cluster.',
    )
    def describe_topic_tool(
        region: str = Field(..., description='AWS region'),
        cluster_arn: str = Field(
            ..., description='The Amazon Resource Name (ARN) that uniquely identifies the cluster'
        ),
        topic_name: str = Field(..., description='The name of the topic to describe'),
    ):
        """
        Returns details for a specific topic on an MSK cluster.

        Args:
            region (str): AWS region
            cluster_arn (str): The Amazon Resource Name (ARN) that uniquely identifies the cluster
            topic_name (str): The name of the topic to describe

        Returns:
            dict: Response containing topic details:
                - TopicArn (str): The Amazon Resource Name (ARN) of the topic
                - TopicName (str): The Kafka topic name of the topic
                - ReplicationFactor (int): The replication factor of the topic
                - PartitionCount (int): The partition count of the topic
                - Configs (str): Topic configurations encoded as a Base64 string
                - Status (str): The status of the topic (CREATING, UPDATING, DELETING, ACTIVE)
        """
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )
        return describe_topic(cluster_arn, topic_name, client)

    @mcp.tool(
        name='describe_topic_partitions',
        description='Returns partition information for a specific topic on an MSK cluster.',
    )
    def describe_topic_partitions_tool(
        region: str = Field(..., description='AWS region'),
        cluster_arn: str = Field(
            ..., description='The Amazon Resource Name (ARN) that uniquely identifies the cluster'
        ),
        topic_name: str = Field(
            ..., description='The name of the topic to describe partitions for'
        ),
        max_results: Optional[int] = Field(
            None, description='Maximum number of partitions to return'
        ),
        next_token: Optional[str] = Field(None, description='Token for pagination'),
    ):
        """
        Returns partition information for a specific topic on an MSK cluster.

        Args:
            region (str): AWS region
            cluster_arn (str): The Amazon Resource Name (ARN) that uniquely identifies the cluster
            topic_name (str): The name of the topic to describe partitions for
            max_results (int, optional): Maximum number of partitions to return
            next_token (str, optional): Token for pagination

        Returns:
            dict: Response containing partition information:
                - Partitions (list): List of partition objects containing:
                    - Partition (int): The partition ID
                    - Leader (int): The leader broker ID for the partition
                    - Replicas (list): List of replica broker IDs for the partition
                    - Isr (list): List of in-sync replica broker IDs for the partition
                - NextToken (str, optional): Token for next page if there are more results
        """
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )

        # Build kwargs conditionally to avoid passing None values
        kwargs = {}
        if max_results is not None:
            kwargs['max_results'] = max_results
        if next_token is not None:
            kwargs['next_token'] = next_token

        return describe_topic_partitions(cluster_arn, topic_name, client, **kwargs)
