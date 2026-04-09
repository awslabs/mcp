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

"""Endpoint management tools for AgentCore Runtime."""

from .error_handler import handle_runtime_error
from .models import (
    CreateEndpointResponse,
    DeleteEndpointResponse,
    EndpointSummary,
    ErrorResponse,
    GetEndpointResponse,
    ListEndpointsResponse,
    UpdateEndpointResponse,
)
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Callable, Optional, Union


class EndpointTools:
    """Tools for managing AgentCore Runtime endpoints."""

    def __init__(self, control_client_factory: Callable) -> None:
        """Initialise with a control-plane client factory.

        Args:
            control_client_factory: Callable returning a boto3 client.
        """
        self._get_client = control_client_factory

    def register(self, mcp) -> None:
        """Register endpoint tools with the MCP server."""
        mcp.tool(name='create_agent_runtime_endpoint')(self.create_agent_runtime_endpoint)
        mcp.tool(name='get_agent_runtime_endpoint')(self.get_agent_runtime_endpoint)
        mcp.tool(name='update_agent_runtime_endpoint')(self.update_agent_runtime_endpoint)
        mcp.tool(name='delete_agent_runtime_endpoint')(self.delete_agent_runtime_endpoint)
        mcp.tool(name='list_agent_runtime_endpoints')(self.list_agent_runtime_endpoints)

    async def create_agent_runtime_endpoint(
        self,
        ctx: Context,
        agent_runtime_id: Annotated[
            str, Field(description='Runtime ID to create the endpoint for.')
        ],
        name: Annotated[
            str,
            Field(description='Endpoint name. Must match [a-zA-Z][a-zA-Z0-9_]{0,47}.'),
        ],
        agent_runtime_version: Annotated[
            Optional[str],
            Field(description='Version to point to. Omit to use latest.'),
        ] = None,
        description: Annotated[
            Optional[str],
            Field(description='Endpoint description (max 256 chars).'),
        ] = None,
    ) -> Union[CreateEndpointResponse, ErrorResponse]:
        """Create a custom endpoint for an AgentCore Runtime.

        Endpoints provide stable access points to specific runtime
        versions. The DEFAULT endpoint is created automatically;
        use this for additional environments (dev, staging, prod).

        This is a configuration operation with no per-use cost.
        """
        try:
            client = self._get_client()
            kwargs: dict = {
                'agentRuntimeId': agent_runtime_id,
                'name': name,
            }
            if agent_runtime_version:
                kwargs['agentRuntimeVersion'] = agent_runtime_version
            if description:
                kwargs['description'] = description

            r = client.create_agent_runtime_endpoint(**kwargs)
            return CreateEndpointResponse(
                status=r.get('status', 'CREATING'),
                agent_runtime_endpoint_arn=r.get('agentRuntimeEndpointArn', ''),
                agent_runtime_id=r.get('agentRuntimeId', ''),
                endpoint_name=r.get('endpointName', ''),
                endpoint_status=r.get('status', ''),
                target_version=r.get('targetVersion', ''),
                created_at=str(r.get('createdAt', '')),
                message='Endpoint creation initiated.',
            )
        except Exception as e:
            return handle_runtime_error('CreateAgentRuntimeEndpoint', e)

    async def get_agent_runtime_endpoint(
        self,
        ctx: Context,
        agent_runtime_id: Annotated[str, Field(description='Runtime ID.')],
        endpoint_name: Annotated[str, Field(description='Endpoint name to retrieve.')],
    ) -> Union[GetEndpointResponse, ErrorResponse]:
        """Get details of a specific runtime endpoint.

        Read-only, no cost implications.
        """
        try:
            client = self._get_client()
            r = client.get_agent_runtime_endpoint(
                agentRuntimeId=agent_runtime_id,
                endpointName=endpoint_name,
            )
            return GetEndpointResponse(
                status='success',
                agent_runtime_endpoint_arn=r.get('agentRuntimeEndpointArn', ''),
                agent_runtime_arn=r.get('agentRuntimeArn', ''),
                endpoint_id=r.get('id', ''),
                endpoint_name=r.get('name', ''),
                description=r.get('description', ''),
                endpoint_status=r.get('status', ''),
                live_version=r.get('liveVersion', ''),
                target_version=r.get('targetVersion', ''),
                failure_reason=r.get('failureReason', ''),
                created_at=str(r.get('createdAt', '')),
                last_updated_at=str(r.get('lastUpdatedAt', '')),
                message='Endpoint retrieved.',
            )
        except Exception as e:
            return handle_runtime_error('GetAgentRuntimeEndpoint', e)

    async def update_agent_runtime_endpoint(
        self,
        ctx: Context,
        agent_runtime_id: Annotated[str, Field(description='Runtime ID.')],
        endpoint_name: Annotated[str, Field(description='Endpoint name to update.')],
        agent_runtime_version: Annotated[
            Optional[str],
            Field(description='New version to point the endpoint to.'),
        ] = None,
        description: Annotated[Optional[str], Field(description='Updated description.')] = None,
    ) -> Union[UpdateEndpointResponse, ErrorResponse]:
        """Update an endpoint to point to a different runtime version.

        Enables zero-downtime version transitions and rollbacks.
        Configuration-only, no per-use cost.
        """
        try:
            client = self._get_client()
            kwargs: dict = {
                'agentRuntimeId': agent_runtime_id,
                'endpointName': endpoint_name,
            }
            if agent_runtime_version:
                kwargs['agentRuntimeVersion'] = agent_runtime_version
            if description is not None:
                kwargs['description'] = description

            r = client.update_agent_runtime_endpoint(**kwargs)
            return UpdateEndpointResponse(
                status=r.get('status', 'UPDATING'),
                agent_runtime_endpoint_arn=r.get('agentRuntimeEndpointArn', ''),
                endpoint_status=r.get('status', ''),
                live_version=r.get('liveVersion', ''),
                target_version=r.get('targetVersion', ''),
                message='Endpoint update initiated.',
            )
        except Exception as e:
            return handle_runtime_error('UpdateAgentRuntimeEndpoint', e)

    async def delete_agent_runtime_endpoint(
        self,
        ctx: Context,
        agent_runtime_id: Annotated[str, Field(description='Runtime ID.')],
        endpoint_name: Annotated[str, Field(description='Endpoint name to delete.')],
    ) -> Union[DeleteEndpointResponse, ErrorResponse]:
        """Delete a runtime endpoint. Cannot delete the DEFAULT endpoint.

        This operation cannot be undone.
        """
        try:
            client = self._get_client()
            r = client.delete_agent_runtime_endpoint(
                agentRuntimeId=agent_runtime_id,
                endpointName=endpoint_name,
            )
            return DeleteEndpointResponse(
                status='success',
                agent_runtime_id=r.get('agentRuntimeId', ''),
                endpoint_name=r.get('endpointName', ''),
                endpoint_status=r.get('status', 'DELETING'),
                message='Endpoint deletion initiated.',
            )
        except Exception as e:
            return handle_runtime_error('DeleteAgentRuntimeEndpoint', e)

    async def list_agent_runtime_endpoints(
        self,
        ctx: Context,
        agent_runtime_id: Annotated[str, Field(description='Runtime ID to list endpoints for.')],
        max_results: Annotated[Optional[int], Field(description='Max results (1-100).')] = None,
        next_token: Annotated[Optional[str], Field(description='Pagination token.')] = None,
    ) -> Union[ListEndpointsResponse, ErrorResponse]:
        """List all endpoints for an AgentCore Runtime.

        Read-only, no cost implications.
        """
        try:
            client = self._get_client()
            kwargs: dict = {'agentRuntimeId': agent_runtime_id}
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token:
                kwargs['nextToken'] = next_token

            r = client.list_agent_runtime_endpoints(**kwargs)
            endpoints = [
                EndpointSummary(
                    agent_runtime_endpoint_arn=ep.get('agentRuntimeEndpointArn', ''),
                    name=ep.get('name', ''),
                    endpoint_id=ep.get('id', ''),
                    live_version=ep.get('liveVersion', ''),
                    target_version=ep.get('targetVersion', ''),
                    endpoint_status=ep.get('status', ''),
                    description=ep.get('description', ''),
                    created_at=str(ep.get('createdAt', '')),
                    last_updated_at=str(ep.get('lastUpdatedAt', '')),
                )
                for ep in r.get('runtimeEndpoints', [])
            ]
            return ListEndpointsResponse(
                status='success',
                endpoints=endpoints,
                next_token=r.get('nextToken'),
                message=f'Found {len(endpoints)} endpoint(s).',
            )
        except Exception as e:
            return handle_runtime_error('ListAgentRuntimeEndpoints', e)
