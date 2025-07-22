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

"""Configuration and Resource Management API Module.

This module provides functions to create and update MSK configurations and manage resources.
"""

import boto3
from ..common_functions import check_mcp_generated_tag
from .create_configuration import create_configuration
from .tag_resource import tag_resource
from .untag_resource import untag_resource
from .update_configuration import update_configuration
from awslabs.aws_msk_mcp_server import __version__
from botocore.config import Config
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Dict, List, Optional


def register_module(mcp: FastMCP) -> None:
    """Registers this tool with the mcp."""

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
        """Create a new MSK configuration.

        Related Resources:
        - resource://msk-documentation/developer-guide - Full MSK Developer Guide with information on configuration properties

        This operation creates a new configuration that can be applied to MSK clusters, allowing you to customize Kafka broker settings.

        === INPUT PARAMETERS ===

        - name (str): The name of the configuration.
        - server_properties (str): Contents of the server.properties file with Kafka configuration settings. Example:
            ```
            auto.create.topics.enable = true
            delete.topic.enable = true
            log.retention.hours = 168
            ```
        - description (str, optional): The description of the configuration.
        - kafka_versions (list, optional): The versions of Apache Kafka with which you can use this configuration. Example:
            ["2.8.1", "3.3.1"]
        - region (str): AWS region where the configuration will be created.

        === OUTPUT (JSON) ===

        {
            "Arn": "arn:aws:kafka:us-west-2:123456789012:configuration/my-configuration/abcd1234-abcd-1234-abcd-1234abcd1234-1",
            "CreationTime": "2023-01-01T12:00:00.000Z",
            "LatestRevision": {
                "CreationTime": "2023-01-01T12:00:00.000Z",
                "Description": "Initial configuration",
                "Revision": 1
            },
            "Name": "my-configuration"
        }

        === NOTES ===

        - After creating a configuration, you should follow up with a tag_resource tool call to add the "MCP Generated" tag.
        - Example: tag_resource_tool(resource_arn=response["Arn"], tags={"MCP Generated": "true"})
        - The server.properties content must follow the Apache Kafka configuration format.
        - Only a subset of Kafka configuration properties are supported by MSK.
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
        """Update an existing MSK configuration.

        Related Resources:
        - resource://msk-documentation/developer-guide - Full MSK Developer Guide with information on configuration properties

        This operation creates a new revision of an existing MSK configuration with updated Kafka broker settings.

        === INPUT PARAMETERS ===

        - arn (str): The Amazon Resource Name (ARN) of the configuration to update.
        - server_properties (str): Updated contents of the server.properties file with Kafka configuration settings. Example:
            ```
            auto.create.topics.enable = true
            delete.topic.enable = true
            log.retention.hours = 168
            ```
        - description (str, optional): The description of the new configuration revision.
        - region (str): AWS region where the configuration is located.

        === OUTPUT (JSON) ===

        {
            "Arn": "arn:aws:kafka:us-west-2:123456789012:configuration/my-configuration/abcd1234-abcd-1234-abcd-1234abcd1234-2",
            "LatestRevision": {
                "CreationTime": "2023-01-02T12:00:00.000Z",
                "Description": "Updated configuration",
                "Revision": 2
            }
        }

        === NOTES ===

        - This operation can ONLY be performed on resources tagged with "MCP Generated".
        - Ensure the resource has this tag before attempting to update it.
        - Each update creates a new revision of the configuration.
        - Existing clusters using this configuration will not automatically use the new revision.
        - You must explicitly update clusters to use the new revision with the update_cluster_configuration tool.
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
        """Add tags to an MSK resource.

        This operation adds key-value tags to an MSK resource for organization, filtering, and access control purposes.

        === INPUT PARAMETERS ===

        - resource_arn (str): The Amazon Resource Name (ARN) of the MSK resource to tag.
        - tags (dict): A map of tag keys and values to add to the resource. Example:
            {
                "Environment": "Production",
                "Owner": "DataTeam",
                "CostCenter": "12345"
            }
        - region (str): AWS region where the resource is located.

        === OUTPUT (JSON) ===

        {}  # Empty response on success

        === NOTES ===

        - Tags are case-sensitive key-value pairs.
        - Each resource can have up to 50 tags.
        - Tag keys can be up to 128 characters, values up to 256 characters.
        - Common tags include: Name, Environment, Owner, Project, CostCenter.
        - The "MCP Generated" tag is used by this system to identify resources it can modify.
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
        """Remove tags from an MSK resource.

        This operation removes specified tags from an MSK resource.

        === INPUT PARAMETERS ===

        - resource_arn (str): The Amazon Resource Name (ARN) of the MSK resource to untag.
        - tag_keys (list): A list of tag keys to remove from the resource. Example:
            ["Environment", "Owner", "CostCenter"]
        - region (str): AWS region where the resource is located.

        === OUTPUT (JSON) ===

        {}  # Empty response on success

        === NOTES ===

        - Only the specified tag keys will be removed; other tags will remain.
        - If a specified tag key doesn't exist on the resource, it is ignored.
        - CAUTION: Do not remove the "MCP Generated" tag if you want to continue managing the resource with MCP tools.
        - Removing tags may affect resource organization, filtering, and access control.
        """
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )
        return untag_resource(resource_arn, tag_keys, client)
