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
Configuration and Resource Management API Module

This module provides functions to create and update MSK configurations and manage resources.
"""

import boto3
from typing import Optional, List, Dict
from botocore.config import Config
from awslabs.aws_msk_mcp_server import __version__
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..common_functions import check_mcp_generated_tag
from .create_configuration import create_configuration
from .tag_resource import tag_resource
from .untag_resource import untag_resource
from .update_configuration import update_configuration


def register_module(mcp: FastMCP) -> None:
    @mcp.tool(name='create_configuration')
    def create_configuration_tool(
        region: str = Field(..., description='AWS region'),
        name: str = Field(..., description='The name of the configuration'),
        server_properties: str = Field(..., description='Contents of the server.properties file'),
        description: Optional[str] = Field('', description='The description of the configuration'),
        kafka_versions: Optional[List[str]] = Field(
            None,
            description='The versions of Apache Kafka with which you can use this MSK configuration',
        ),
    ):
        """
        Create a new MSK configuration.

        Args:
            name (str): The name of the configuration
            server_properties (str): Contents of the server.properties file.
                                    Supported properties are documented in the MSK Developer Guide
                Example: "auto.create.topics.enable=true\ndelete.topic.enable=true"
            description (str, optional): The description of the configuration
            kafka_versions (list, optional): The versions of Apache Kafka with which you can use this MSK configuration
                Example: ["2.8.1", "3.3.1"]
            region (str): AWS region

        Returns:
            dict: Result of the create operation containing:
                - Arn (str): The Amazon Resource Name (ARN) of the configuration
                - CreationTime (datetime): The time when the configuration was created
                - LatestRevision (dict): Information about the latest revision including:
                    - CreationTime (datetime): The time when the revision was created
                    - Description (str): The description of the revision
                    - Revision (int): The revision number
                - Name (str): The name of the configuration

        Note:
            After creating a configuration, you should follow up with a tag_resource tool call
            to add the "MCP Generated" tag to the created resource.
            Example:
            tag_resource_tool(resource_arn=response["Arn"], tags={"MCP Generated": "true"})
        """
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )
        return create_configuration(name, server_properties, client, description, kafka_versions)

    @mcp.tool(name='update_configuration')
    def update_configuration_tool(
        region: str = Field(..., description='AWS region'),
        arn: str = Field(
            ..., description='The Amazon Resource Name (ARN) of the configuration to update'
        ),
        server_properties: str = Field(..., description='Contents of the server.properties file'),
        description: Optional[str] = Field(
            '', description='The description of the configuration revision'
        ),
    ):
        """
        Update an existing MSK configuration.

        Args:
            arn (str): The Amazon Resource Name (ARN) of the configuration to update
            server_properties (str): Contents of the server.properties file.
                                    Supported properties are documented in the MSK Developer Guide
                Example: "auto.create.topics.enable=true\ndelete.topic.enable=true"
            description (str, optional): The description of the configuration revision
            region (str): AWS region

        Returns:
            dict: Result of the update operation containing:
                - Arn (str): The Amazon Resource Name (ARN) of the configuration
                - LatestRevision (dict): Information about the latest revision including:
                    - CreationTime (datetime): The time when the revision was created
                    - Description (str): The description of the revision
                    - Revision (int): The revision number

        Note:
            This operation can ONLY be performed on resources tagged with "MCP Generated".
            Ensure the resource has this tag before attempting to update it.
        """
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )

        # Check if the resource has the "MCP Generated" tag
        if not check_mcp_generated_tag(arn, client):
            raise ValueError(
                f"Resource {arn} does not have the 'MCP Generated' tag. "
                "This operation can only be performed on resources tagged with 'MCP Generated'."
            )

        return update_configuration(arn, server_properties, client, description)

    @mcp.tool(name='tag_resource')
    def tag_resource_tool(
        region: str = Field(..., description='AWS region'),
        resource_arn: str = Field(
            ..., description='The Amazon Resource Name (ARN) of the resource'
        ),
        tags: Dict[str, str] = Field(..., description='A map of tags to add to the resource'),
    ):
        """
        Add tags to an MSK resource.

        Args:
            resource_arn (str): The Amazon Resource Name (ARN) of the resource
            tags (dict): A map of tags to add to the resource
                Example: {"Environment": "Production", "Owner": "DataTeam"}
            region (str): AWS region

        Returns:
            dict: Empty response if successful
        """
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )
        return tag_resource(resource_arn, tags, client)

    @mcp.tool(name='untag_resource')
    def untag_resource_tool(
        region: str = Field(..., description='AWS region'),
        resource_arn: str = Field(
            ..., description='The Amazon Resource Name (ARN) of the resource'
        ),
        tag_keys: List[str] = Field(
            ..., description='A list of tag keys to remove from the resource'
        ),
    ):
        """
        Remove tags from an MSK resource.

        Args:
            resource_arn (str): The Amazon Resource Name (ARN) of the resource
            tag_keys (list): A list of tag keys to remove from the resource
                Example: ["Environment", "Owner"]
            region (str): AWS region

        Returns:
            dict: Empty response if successful
        """
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )
        return untag_resource(resource_arn, tag_keys, client)
