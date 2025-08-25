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

"""Create API Key tool for AWS AppSync MCP Server."""

from awslabs.aws_appsync_mcp_server.decorators import write_operation
from awslabs.aws_appsync_mcp_server.operations.create_api_key import create_api_key_operation
from mcp.types import ToolAnnotations
from pydantic import Field
from typing import Annotated, Dict, Optional


def register_create_api_key_tool(mcp):
    """Register the create_api_key tool with the MCP server."""

    @mcp.tool(
        name='create_api_key',
        description="""Creates a unique key that you can distribute to clients who invoke your API.

        This operation creates an API key for the specified GraphQL API. API keys are used
        to authenticate requests when the API uses API_KEY authentication type.
        """,
        annotations=ToolAnnotations(
            title='Create API Key', readOnlyHint=False, destructiveHint=False, openWorldHint=False
        ),
    )
    @write_operation
    async def create_api_key(
        api_id: Annotated[str, Field(description='The ID for the GraphQL API')],
        description: Annotated[
            Optional[str], Field(description='A description of the purpose of the API key')
        ] = None,
        expires: Annotated[
            Optional[int],
            Field(
                description='From the creation time, the time after which the API key expires (Unix timestamp)'
            ),
        ] = None,
    ) -> Dict:
        """Creates a unique key that you can distribute to clients who invoke your API.

        This operation creates an API key for the specified GraphQL API. API keys are used
        to authenticate requests when the API uses API_KEY authentication type.

        Args:
            api_id: The ID for the GraphQL API for which you want to create an API key.
            description: Optional description of the purpose of the API key.
            expires: Optional expiration time for the API key as a Unix timestamp.
                    If not provided, the API key will not expire.

        Returns:
            A dictionary containing information about the created API key, including:
            - apiKey: The API key object with details like id, description, expires, etc.
        """
        return await create_api_key_operation(api_id, description, expires)
