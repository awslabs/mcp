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

"""Control plane tools for AgentCore Memory resource management.

Provides tools to create, get, update, delete, and list Memory resources.
"""

from .error_handler import handle_memory_error
from .models import (
    DeleteMemoryResponse,
    ErrorResponse,
    ListMemoriesResponse,
    MemoryResponse,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any


class ControlPlaneTools:
    """Tools for managing AgentCore Memory resources (control plane)."""

    def __init__(self, client_factory):
        """Initialize with a callable that returns a boto3 control plane client."""
        self._get_client = client_factory

    def register(self, mcp):
        """Register control plane tools with the MCP server."""
        mcp.tool(name='memory_create')(self.memory_create)
        mcp.tool(name='memory_get')(self.memory_get)
        mcp.tool(name='memory_update')(self.memory_update)
        mcp.tool(name='memory_delete')(self.memory_delete)
        mcp.tool(name='memory_list')(self.memory_list)

    async def memory_create(
        self,
        ctx: Context,
        name: Annotated[
            str,
            Field(
                description=(
                    'Unique name for the memory resource. Pattern: [a-zA-Z][a-zA-Z0-9_]{0,47}'
                )
            ),
        ],
        event_expiry_duration: Annotated[
            int,
            Field(description='Days after which memory events expire (3-365)'),
        ],
        description: Annotated[
            str | None,
            Field(description='Description of the memory resource (1-4096 chars)'),
        ] = None,
        encryption_key_arn: Annotated[
            str | None,
            Field(description='KMS key ARN for encryption'),
        ] = None,
        memory_execution_role_arn: Annotated[
            str | None,
            Field(description='IAM role ARN for memory execution'),
        ] = None,
        memory_strategies: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    'List of memory strategy configurations. Each is a union '
                    'with one key: semanticMemoryStrategy, summaryMemoryStrategy, '
                    'userPreferenceMemoryStrategy, episodicMemoryStrategy, or '
                    'customMemoryStrategy. Each strategy requires a "name" field.'
                )
            ),
        ] = None,
        tags: Annotated[
            dict[str, str] | None,
            Field(description='Tags as key-value pairs (max 50)'),
        ] = None,
    ) -> MemoryResponse | ErrorResponse:
        """Create a new AgentCore Memory resource.

        COST WARNING: Creating a memory resource provisions AWS infrastructure.
        This incurs AWS charges. Memory strategies that process events
        (extraction, consolidation) consume additional compute resources.

        The memory resource starts in CREATING status and transitions to
        ACTIVE when ready. Use memory_get to check status.

        Returns the created memory resource details including its ID.
        """
        logger.info(f'Creating memory resource: {name}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                'name': name,
                'eventExpiryDuration': event_expiry_duration,
            }
            if description is not None:
                kwargs['description'] = description
            if encryption_key_arn is not None:
                kwargs['encryptionKeyArn'] = encryption_key_arn
            if memory_execution_role_arn is not None:
                kwargs['memoryExecutionRoleArn'] = memory_execution_role_arn
            if memory_strategies is not None:
                kwargs['memoryStrategies'] = memory_strategies
            if tags is not None:
                kwargs['tags'] = tags

            response = client.create_memory(**kwargs)
            memory = response.get('memory', {})

            return MemoryResponse(
                status='success',
                message=f'Memory "{name}" created. ID: {memory.get("id", "unknown")}. '
                f'Status: {memory.get("status", "CREATING")}.',
                memory=memory,
            )
        except Exception as e:
            return handle_memory_error('CreateMemory', e)

    async def memory_get(
        self,
        ctx: Context,
        memory_id: Annotated[
            str,
            Field(description='Memory resource ID (min 12 chars)'),
        ],
    ) -> MemoryResponse | ErrorResponse:
        """Get details of an AgentCore Memory resource.

        Returns the memory resource including status, strategies,
        configuration, and timestamps. This is a read-only operation
        with no cost implications.
        """
        logger.info(f'Getting memory: {memory_id}')

        try:
            client = self._get_client()
            response = client.get_memory(memoryId=memory_id)
            memory = response.get('memory', {})

            return MemoryResponse(
                status='success',
                message=f'Memory {memory_id} retrieved. '
                f'Status: {memory.get("status", "UNKNOWN")}.',
                memory=memory,
            )
        except Exception as e:
            return handle_memory_error('GetMemory', e)

    async def memory_update(
        self,
        ctx: Context,
        memory_id: Annotated[
            str,
            Field(description='Memory resource ID to update'),
        ],
        description: Annotated[
            str | None,
            Field(description='Updated description (1-4096 chars)'),
        ] = None,
        event_expiry_duration: Annotated[
            int | None,
            Field(description='Updated event expiry in days (3-365)'),
        ] = None,
        memory_execution_role_arn: Annotated[
            str | None,
            Field(description='Updated IAM role ARN'),
        ] = None,
        memory_strategies: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Strategy modifications. Object with optional keys: '
                    '"addMemoryStrategies" (list of strategy inputs), '
                    '"deleteMemoryStrategies" (list of {memoryStrategyId}), '
                    '"modifyMemoryStrategies" (list of modifications).'
                )
            ),
        ] = None,
    ) -> MemoryResponse | ErrorResponse:
        """Update an AgentCore Memory resource.

        COST WARNING: Adding new memory strategies may increase processing
        costs as new strategies will process incoming events.

        Can update description, event expiry, execution role, and strategies
        (add, modify, or delete). Returns the updated memory details.
        """
        logger.info(f'Updating memory: {memory_id}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {'memoryId': memory_id}
            if description is not None:
                kwargs['description'] = description
            if event_expiry_duration is not None:
                kwargs['eventExpiryDuration'] = event_expiry_duration
            if memory_execution_role_arn is not None:
                kwargs['memoryExecutionRoleArn'] = memory_execution_role_arn
            if memory_strategies is not None:
                kwargs['memoryStrategies'] = memory_strategies

            response = client.update_memory(**kwargs)
            memory = response.get('memory', {})

            return MemoryResponse(
                status='success',
                message=f'Memory {memory_id} updated.',
                memory=memory,
            )
        except Exception as e:
            return handle_memory_error('UpdateMemory', e)

    async def memory_delete(
        self,
        ctx: Context,
        memory_id: Annotated[
            str,
            Field(description='Memory resource ID to delete'),
        ],
    ) -> DeleteMemoryResponse | ErrorResponse:
        """Delete an AgentCore Memory resource.

        WARNING: This permanently deletes the memory resource and all
        associated data (events, memory records, strategies). This
        action cannot be undone.
        """
        logger.info(f'Deleting memory: {memory_id}')

        try:
            client = self._get_client()
            response = client.delete_memory(memoryId=memory_id)

            return DeleteMemoryResponse(
                status='success',
                message=f'Memory {memory_id} deletion requested.',
                memory_id=response.get('memoryId', memory_id),
                memory_status=response.get('status', 'DELETING'),
            )
        except Exception as e:
            return handle_memory_error('DeleteMemory', e)

    async def memory_list(
        self,
        ctx: Context,
        max_results: Annotated[
            int | None,
            Field(description='Max results per page (1-100)'),
        ] = None,
        next_token: Annotated[
            str | None,
            Field(description='Pagination token from previous response'),
        ] = None,
    ) -> ListMemoriesResponse | ErrorResponse:
        """List all AgentCore Memory resources in the account.

        Returns memory summaries with IDs, ARNs, status, and timestamps.
        This is a read-only operation with no cost implications.
        """
        logger.info('Listing memories')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {}
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token is not None:
                kwargs['nextToken'] = next_token

            response = client.list_memories(**kwargs)

            memories = response.get('memories', [])
            return ListMemoriesResponse(
                status='success',
                message=f'Found {len(memories)} memory resource(s).',
                memories=memories,
                next_token=response.get('nextToken'),
            )
        except Exception as e:
            return handle_memory_error('ListMemories', e)
