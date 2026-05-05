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

"""Create API tool for AWS AppSync MCP Server."""

from awslabs.aws_appsync_mcp_server.decorators import write_operation
from awslabs.aws_appsync_mcp_server.operations.create_api import create_api_operation
from mcp.types import ToolAnnotations
from pydantic import Field
from typing import Annotated, Dict, Optional


def register_create_api_tool(mcp):
    """Register the create_api tool with the MCP server."""

    @mcp.tool(
        name='create_api',
        description="""Creates a new AppSync API.

        This operation creates a new AppSync API with the specified configuration.
        The API will be created with default settings and can be further configured
        using additional AppSync operations.
        """,
        annotations=ToolAnnotations(
            title='Create AppSync API',
            readOnlyHint=False,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    @write_operation
    async def create_api(
        name: Annotated[str, Field(description='The name of the API')],
        owner_contact: Annotated[
            Optional[str], Field(description='The owner contact information for the API')
        ] = None,
        tags: Annotated[
            Optional[Dict[str, str]], Field(description='A map of tags to assign to the resource')
        ] = None,
        event_config: Annotated[
            Optional[Dict], Field(description='The event configuration for the API')
        ] = None,
    ) -> Dict:
        """Creates a new AppSync API.

        This operation creates a new AppSync API with the specified configuration.
        The API will be created with default settings and can be further configured
        using additional AppSync operations.

        Args:
            name: The name of the API. This name must be unique within your AWS account.
            owner_contact: Optional contact information for the API owner.
            tags: Optional map of tags to assign to the API resource.
            event_config: Optional event configuration for real-time subscriptions.

        Returns:
            A dictionary containing information about the created API, including:
            - api: The API object with details like apiId, name etc.

        Example response:
            {
                "api": {
                    "apiId": "abcdefghijklmnopqrstuvwxyz",
                    "name": "my-graphql-api",
                    "ownerContact": "owner@example.com",
                    "tags": {"Environment": "dev"},
                    "dns": {...},
                    "apiArn": "arn:aws:appsync:us-east-1:123456789012:apis/abcdefghijklmnopqrstuvwxyz",
                    "created": "2024-01-01T00:00:00Z",
                    "xrayEnabled": false
                }
            }
        """
        return await create_api_operation(name, owner_contact, tags, event_config)
