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

"""Create Schema tool for AWS AppSync MCP Server."""

from awslabs.aws_appsync_mcp_server.decorators import write_operation
from awslabs.aws_appsync_mcp_server.operations.create_schema import create_schema_operation
from mcp.types import ToolAnnotations
from pydantic import Field
from typing import Annotated, Dict


def register_create_schema_tool(mcp):
    """Register the create_schema tool with the MCP server."""

    @mcp.tool(
        name='create_schema',
        description="""Creates a GraphQL schema for an AppSync API and polls until completion.

        This tool starts the schema creation process and automatically polls for the status
        until the operation completes (either SUCCESS or FAILED). The schema defines the
        structure of your GraphQL API, including types, queries, mutations, and subscriptions.
        """,
        annotations=ToolAnnotations(
            title='Create Schema', readOnlyHint=False, destructiveHint=False, openWorldHint=False
        ),
    )
    @write_operation
    async def create_schema(
        api_id: Annotated[str, Field(description='The API ID for the GraphQL API')],
        definition: Annotated[
            str,
            Field(description='The schema definition in GraphQL Schema Definition Language (SDL)'),
        ],
    ) -> Dict:
        """Creates a GraphQL schema for an AppSync API and polls until completion.

        This tool starts the schema creation process and automatically polls for the status
        until the operation completes. The schema defines the structure of your GraphQL API.

        Args:
            api_id: The API ID for the GraphQL API.
            definition: The schema definition in GraphQL Schema Definition Language (SDL).

        Returns:
            A dictionary containing the final status and details of the schema creation:
            - status: The final status (SUCCESS or FAILED)
            - details: Additional details about the schema creation result

        Example response:
            {
                "status": "SUCCESS",
                "details": "Schema created successfully"
            }
        """
        return await create_schema_operation(api_id, definition)
