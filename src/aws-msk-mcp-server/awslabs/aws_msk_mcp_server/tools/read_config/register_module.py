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

"""Configuration and Resource Information API Module.

This module provides functions to retrieve information about MSK configurations and resources.
"""

import boto3
from .describe_configuration import describe_configuration
from .describe_configuration_revision import describe_configuration_revision
from .list_configuration_revisions import list_configuration_revisions
from .list_tags_for_resource import list_tags_for_resource
from awslabs.aws_msk_mcp_server import __version__
from botocore.config import Config
from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register_module(mcp: FastMCP) -> None:
    """Registers this tool with the mcp."""

    @mcp.tool(
        name='get_configuration_info',
        description="""Get detailed information about MSK configurations and their revisions.

This operation provides detailed information about MSK configurations and their revisions.

=== ACTION MODES ===

1. action = "describe"
- Retrieves basic information about a configuration.

Required parameters:
- arn (str): The ARN of the configuration
- region (str): AWS region

Output (JSON):
{
    "Arn": "arn:aws:kafka:us-west-2:123456789012:configuration/my-configuration/abcd1234",
    "CreationTime": "2023-01-01T12:00:00.000Z",
    "Description": "My MSK configuration",
    "KafkaVersions": ["2.8.1", "3.3.1"],
    "LatestRevision": {
        "CreationTime": "2023-01-01T12:00:00.000Z",
        "Description": "Initial configuration",
        "Revision": 1
    },
    "Name": "my-configuration",
    "State": "ACTIVE"
}

2. action = "revisions"
- Lists all revisions for a configuration.

Required parameters:
- arn (str): The ARN of the configuration
- region (str): AWS region

Optional parameters:
- max_results (int): Maximum number of revisions to return (default: 10)
- next_token (str): Token for pagination

Output (JSON):
{
    "Revisions": [
        {
            "CreationTime": "2023-01-02T12:00:00.000Z",
            "Description": "Updated configuration",
            "Revision": 2
        },
        {
            "CreationTime": "2023-01-01T12:00:00.000Z",
            "Description": "Initial configuration",
            "Revision": 1
        }
    ],
    "NextToken": "AAAABBBCCC"
}

3. action = "revision_details"
- Retrieves detailed information about a specific configuration revision.

Required parameters:
- arn (str): The ARN of the configuration
- region (str): AWS region
- revision (int): The revision number to describe

Output (JSON):
{
    "Arn": "arn:aws:kafka:us-west-2:123456789012:configuration/my-configuration/abcd1234",
    "CreationTime": "2023-01-01T12:00:00.000Z",
    "Description": "Initial configuration",
    "Revision": 1,
    "ServerProperties": "auto.create.topics.enable=true\ndelete.topic.enable=true\nlog.retention.hours=168"
}

=== NOTES ===

- Configuration revisions are immutable; each change creates a new revision.
- The ServerProperties field contains the actual Kafka broker configuration settings.
- To apply a configuration to a cluster, use the update_cluster_configuration tool with the configuration ARN and revision number.
- Configurations can be associated with multiple Kafka versions.""",
    )
    def get_configuration_info(
        region: str = Field(..., description='AWS region'),
        action: str = Field(
            ...,
            description="The operation to perform: 'describe', 'revisions', or 'revision_details'",
        ),
        arn: str = Field(..., description='The Amazon Resource Name (ARN) of the configuration'),
        kwargs: dict = Field({}, description='Additional arguments based on the action'),
    ):
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

    @mcp.tool(
        name='list_tags_for_resource',
        description="""List all tags associated with an MSK resource.

This operation retrieves all tags associated with an MSK resource.

=== INPUT PARAMETERS ===

- arn (str): The Amazon Resource Name (ARN) of the MSK resource.
- region (str): AWS region where the resource is located.

=== OUTPUT (JSON) ===

{
    "Tags": {
        "Name": "production-cluster",
        "Environment": "Production",
        "Owner": "DataTeam",
        "CostCenter": "12345",
        "MCP Generated": "true"
    }
}

=== NOTES ===

- Tags are key-value pairs used for resource organization and management.
- The "MCP Generated" tag is used by this system to identify resources it can modify.
- Tags can be used for cost allocation, access control, and resource grouping.""",
    )
    def list_tags_for_resource_tool(
        region: str = Field(description='AWS region'),
        arn: str = Field(description='The Amazon Resource Name (ARN) of the resource'),
    ):
        # Create a boto3 client
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )
        return list_tags_for_resource(arn, client)
