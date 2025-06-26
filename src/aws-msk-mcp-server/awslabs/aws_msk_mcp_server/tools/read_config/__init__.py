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
Configuration and Resource Information API Module

This module provides functions to retrieve information about MSK configurations and resources.
"""

import boto3
from botocore.config import Config
from awslabs.aws_msk_mcp_server import __version__
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .describe_configuration import describe_configuration
from .describe_configuration_revision import describe_configuration_revision
from .list_configuration_revisions import list_configuration_revisions
from .list_tags_for_resource import list_tags_for_resource


def register_module(mcp: FastMCP) -> None:
    @mcp.tool(name='get_configuration_info')
    def get_configuration_info(
        region: str = Field(..., description='AWS region'),
        action: str = Field(
            ...,
            description="The operation to perform: 'describe', 'revisions', or 'revision_details'",
        ),
        arn: str = Field(..., description='The Amazon Resource Name (ARN) of the configuration'),
        kwargs: dict = Field({}, description='Additional arguments based on the action'),
    ):
        """
        Get information about MSK configurations.

        Args:
            action (str): The operation to perform:
                - 'describe': Get basic configuration information
                - 'revisions': List all revisions for a configuration
                - 'revision_details': Get details about a specific revision
            arn (str): The Amazon Resource Name (ARN) of the configuration
            region (str): AWS region
            kwargs (dict, optional): Additional arguments based on the action:
                - For 'revisions':
                    - max_results (int, optional): Maximum number of results to return (default: 10)
                    - next_token (str, optional): Pagination token for subsequent requests
                - For 'revision_details':
                    - revision (int, required): The revision number to describe

        Returns:
            dict: Configuration information based on the requested action:
                - For 'describe': Basic configuration information including:
                    - Arn: The Amazon Resource Name (ARN) of the configuration
                    - CreationTime: The time when the configuration was created
                    - Description: The description of the configuration
                    - KafkaVersions: The versions of Apache Kafka with which you can use this configuration
                    - LatestRevision: Information about the latest revision
                    - Name: The name of the configuration
                    - State: The state of the configuration (ACTIVE, DELETING, DELETE_FAILED)

                - For 'revisions': List of configuration revisions including:
                    - NextToken: The pagination token for subsequent requests
                    - Revisions: List of configuration revision information

                - For 'revision_details': Information about the specific revision including:
                    - Arn: The Amazon Resource Name (ARN) of the configuration
                    - CreationTime: The time when the configuration was created
                    - Description: The description of the configuration revision
                    - Revision: The revision number
                    - ServerProperties: Contents of the server.properties file

        Examples:
            # Get basic configuration information
            get_configuration_info(action="describe", arn="arn:aws:kafka:us-east-1:123456789012:configuration/example-config")

            # List all revisions for a configuration
            get_configuration_info(action="revisions", arn="arn:aws:kafka:us-east-1:123456789012:configuration/example-config", max_results=20)

            # Get details about a specific revision
            get_configuration_info(action="revision_details", arn="arn:aws:kafka:us-east-1:123456789012:configuration/example-config", revision=3)
        """
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )

        if action == 'describe':
            return describe_configuration(arn, client)
        elif action == 'revisions':
            max_results = kwargs.get('max_results', 10)
            next_token = kwargs.get('next_token', '')
            return list_configuration_revisions(
                arn, client, max_results=max_results, next_token=next_token
            )
        elif action == 'revision_details':
            revision = kwargs.get('revision')
            if not revision:
                raise ValueError('Revision number is required for revision_details action')
            return describe_configuration_revision(arn, revision, client)
        else:
            raise ValueError(
                f'Unsupported action: {action}. Supported actions are: describe, revisions, revision_details'
            )

    @mcp.tool(name='list_tags_for_resource')
    def list_tags_for_resource_tool(
        region: str = Field(description='AWS region'),
        arn: str = Field(description='The Amazon Resource Name (ARN) of the resource'),
    ):
        """
        List all tags for an MSK resource.

        Args:
            arn (str): The Amazon Resource Name (ARN) of the resource
            region (str): AWS region

        Returns:
            dict: Tags for the resource in the format:
                {
                    "Tags": {
                        "Key1": "Value1",
                        "Key2": "Value2"
                    }
                }
        """
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )
        return list_tags_for_resource(arn, client)
