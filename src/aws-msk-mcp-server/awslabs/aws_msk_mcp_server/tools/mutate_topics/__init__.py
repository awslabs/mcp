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
Topics Management API Module

This module provides functions to manage topics in MSK clusters.
"""

from typing import Optional

import boto3
from botocore.config import Config
from awslabs.aws_msk_mcp_server import __version__
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..common_functions import check_mcp_generated_tag
from .create_topic import create_topic
from .delete_topic import delete_topic
from .update_topic import update_topic


def register_module(mcp: FastMCP) -> None:
    @mcp.tool(name='create_topic', description='Creates a topic in the specified MSK cluster.')
    def create_topic_tool(
        region: str = Field(..., description='AWS region'),
        cluster_arn: str = Field(
            ..., description='The Amazon Resource Name (ARN) that uniquely identifies the cluster'
        ),
        topic_name: str = Field(..., description='The name of the topic to create'),
        partition_count: int = Field(..., description='The number of partitions for the topic'),
        replication_factor: int = Field(..., description='The replication factor for the topic'),
        configs: Optional[str] = Field(
            None, description='Topic configurations encoded as a Base64 string'
        ),
    ):
        """
        Creates a topic in the specified MSK cluster.

        Args:
            region (str): AWS region
            cluster_arn (str): The Amazon Resource Name (ARN) that uniquely identifies the cluster
            topic_name (str): The name of the topic to create
            partition_count (int): The number of partitions for the topic
            replication_factor (int): The replication factor for the topic
            configs (str, optional): Topic configurations encoded as a Base64 string

        Returns:
            dict: Response containing topic creation result:
                - TopicArn (str): The Amazon Resource Name (ARN) of the topic
                - TopicName (str): The name of the topic that was created
                - Status (str): The status of the topic creation (CREATING, UPDATING, DELETING, ACTIVE)

        Note:
            This operation can ONLY be performed on resources tagged with "MCP Generated".
            Ensure the cluster has this tag before attempting to create topics.
        """
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )

        # Check if the resource has the "MCP Generated" tag
        if not check_mcp_generated_tag(cluster_arn, client):
            raise ValueError(
                f"Resource {cluster_arn} does not have the 'MCP Generated' tag. "
                "This operation can only be performed on resources tagged with 'MCP Generated'."
            )

        # Call create_topic with configs only if provided
        if configs is not None:
            return create_topic(
                cluster_arn, topic_name, partition_count, replication_factor, client, configs
            )
        else:
            return create_topic(
                cluster_arn, topic_name, partition_count, replication_factor, client
            )

    @mcp.tool(
        name='update_topic',
        description='Updates the configuration of the specified topic.',
    )
    def update_topic_tool(
        region: str = Field(..., description='AWS region'),
        cluster_arn: str = Field(
            ..., description='The Amazon Resource Name (ARN) that uniquely identifies the cluster'
        ),
        topic_name: str = Field(
            ..., description='The name of the topic to update configuration for'
        ),
        configs: Optional[str] = Field(
            None, description='The new topic configurations encoded as a Base64 string'
        ),
        partition_count: Optional[int] = Field(
            None, description='The new total number of partitions for the topic'
        ),
    ):
        """
        Updates the configuration of the specified topic.

        Args:
            region (str): AWS region
            cluster_arn (str): The Amazon Resource Name (ARN) that uniquely identifies the cluster
            topic_name (str): The name of the topic to update configuration for
            configs (str, optional): The new topic configurations encoded as a Base64 string
            partition_count (int, optional): The new total number of partitions for the topic

        Returns:
            dict: Response containing topic update result:
                - TopicArn (str): The Amazon Resource Name (ARN) of the topic
                - TopicName (str): The name of the topic whose configuration was updated
                - Status (str): The status of the topic update (CREATING, UPDATING, DELETING, ACTIVE)

        Note:
            This operation can ONLY be performed on resources tagged with "MCP Generated".
            Ensure the cluster has this tag before attempting to update topics.
        """
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )

        # Check if the resource has the "MCP Generated" tag
        if not check_mcp_generated_tag(cluster_arn, client):
            raise ValueError(
                f"Resource {cluster_arn} does not have the 'MCP Generated' tag. "
                "This operation can only be performed on resources tagged with 'MCP Generated'."
            )

        # Build kwargs conditionally to avoid passing None values
        kwargs = {}
        if configs is not None:
            kwargs['configs'] = configs
        if partition_count is not None:
            kwargs['partition_count'] = partition_count

        return update_topic(cluster_arn, topic_name, client, **kwargs)

    @mcp.tool(name='delete_topic', description='Deletes a topic in the specified MSK cluster.')
    def delete_topic_tool(
        region: str = Field(..., description='AWS region'),
        cluster_arn: str = Field(
            ..., description='The Amazon Resource Name (ARN) that uniquely identifies the cluster'
        ),
        topic_name: str = Field(..., description='The name of the topic to delete'),
        confirm_delete: str = Field(
            ..., description='Must be exactly "DELETE" to confirm the destructive operation'
        ),
    ):
        """
        Deletes a topic in the specified MSK cluster.

        SAFETY REQUIREMENTS:
        1. confirm_delete parameter must be exactly "DELETE" (case-sensitive)
        2. Topics with system prefixes (__amazon*, __consumer*) are protected

        WARNING: This is a destructive operation that permanently deletes the topic and all its data.

        Args:
            region (str): AWS region
            cluster_arn (str): The Amazon Resource Name (ARN) that uniquely identifies the cluster
            topic_name (str): The name of the topic to delete
            confirm_delete (str): Must be exactly "DELETE" to confirm the destructive operation

        Returns:
            dict: Response containing topic deletion result:
                - TopicArn (str): The Amazon Resource Name (ARN) of the topic
                - TopicName (str): The name of the topic that was deleted
                - Status (str): The status of the topic deletion (CREATING, UPDATING, DELETING, ACTIVE)

        Raises:
            ValueError: If confirm_delete is not "DELETE" or if topic has protected system prefix

        Note:
            This operation can ONLY be performed on resources tagged with "MCP Generated".
            Ensure the cluster has this tag before attempting to delete topics.
        """
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )

        # Check if the resource has the "MCP Generated" tag
        if not check_mcp_generated_tag(cluster_arn, client):
            raise ValueError(
                f"Resource {cluster_arn} does not have the 'MCP Generated' tag. "
                "This operation can only be performed on resources tagged with 'MCP Generated'."
            )

        return delete_topic(cluster_arn, topic_name, client, confirm_delete)
