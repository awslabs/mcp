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

"""Create Channel Namespace tool for AWS AppSync MCP Server."""

from awslabs.aws_appsync_mcp_server.decorators import write_operation
from awslabs.aws_appsync_mcp_server.operations.create_channel_namespace import (
    create_channel_namespace_operation,
)
from mcp.types import ToolAnnotations
from pydantic import Field
from typing import Annotated, Dict, List, Optional


def register_create_channel_namespace_tool(mcp):
    """Register the create_channel_namespace tool with the MCP server."""

    @mcp.tool(
        name='create_channel_namespace',
        description="""Creates a ChannelNamespace for an Api.

        This operation creates a channel namespace for the specified GraphQL API.
        Channel namespaces provide a way to organize and manage real-time subscriptions
        in AppSync APIs, enabling event-driven architectures and real-time data updates.
        """,
        annotations=ToolAnnotations(
            title='Create Channel Namespace',
            readOnlyHint=False,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    @write_operation
    async def create_channel_namespace(
        api_id: Annotated[
            str, Field(description='The ID of the Api associated with the ChannelNamespace')
        ],
        name: Annotated[str, Field(description='The name of the ChannelNamespace')],
        subscribe_auth_modes: Annotated[
            Optional[List[Dict]],
            Field(
                description='The authorization mode to use for subscribing to messages on the channel namespace'
            ),
        ] = None,
        publish_auth_modes: Annotated[
            Optional[List[Dict]],
            Field(
                description='The authorization mode to use for publishing messages on the channel namespace'
            ),
        ] = None,
        code_handlers: Annotated[
            Optional[str],
            Field(
                description='The event handler functions that run custom business logic to process published events and subscribe requests'
            ),
        ] = None,
        handler_configs: Annotated[
            Optional[Dict],
            Field(
                description='Configuration for event handlers that process published events and subscribe requests'
            ),
        ] = None,
        tags: Annotated[
            Optional[Dict[str, str]], Field(description='A map of tags to assign to the resource')
        ] = None,
    ) -> Dict:
        """Creates a ChannelNamespace for an Api.

        This operation creates a channel namespace for the specified GraphQL API.
        Channel namespaces provide a way to organize and manage real-time subscriptions
        in AppSync APIs, enabling event-driven architectures and real-time data updates.

        Args:
            api_id: The ID of the Api associated with the ChannelNamespace.
            name: The name of the ChannelNamespace. Must be unique within the API.
            subscribe_auth_modes: Optional list of authorization modes for subscribing to messages.
                Each auth mode is a dictionary with 'authType' and optional configuration.
            publish_auth_modes: Optional list of authorization modes for publishing messages.
                Each auth mode is a dictionary with 'authType' and optional configuration.
            code_handlers: Optional event handler functions that run custom business logic
                to process published events and subscribe requests.
            handler_configs: Optional configuration for event handlers that process published
                events and subscribe requests. Dictionary containing handler configuration.
            tags: Optional map of tags to assign to the resource.

        Returns:
            A dictionary containing information about the created channel namespace, including:
            - channelNamespace: The ChannelNamespace object with details like name, ARN, auth modes, etc.

        Example response:
            {
                "channelNamespace": {
                    "apiId": "API_ID",
                    "name": "MyChannelNamespace",
                    "channelNamespaceArn": "arn:aws:appsync:us-east-1:123456789012:apis/graphqlapiid/channelNamespace/channelNamespaceName",
                    "subscribeAuthModes": [...],
                    "publishAuthModes": [...],
                    "creationDate": "2023-01-01T00:00:00Z",
                    "lastModifiedDate": "2023-01-01T00:00:00Z"
                }
            }
        """
        return await create_channel_namespace_operation(
            api_id,
            name,
            subscribe_auth_modes,
            publish_auth_modes,
            code_handlers,
            handler_configs,
            tags,
        )
