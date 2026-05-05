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

"""Memory record tools for AgentCore Memory data plane.

Memory records are structured units of long-term memory extracted from
events by memory strategies. They can also be created/updated directly
via batch operations.
"""

from .error_handler import handle_memory_error
from .models import (
    BatchRecordsResponse,
    DeleteMemoryRecordResponse,
    ErrorResponse,
    ListMemoryRecordsResponse,
    MemoryRecordResponse,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any


class RecordTools:
    """Tools for managing memory records in AgentCore Memory."""

    def __init__(self, client_factory):
        """Initialize with a callable that returns a boto3 data plane client."""
        self._get_client = client_factory

    def register(self, mcp):
        """Register memory record tools with the MCP server."""
        mcp.tool(name='memory_get_record')(self.memory_get_record)
        mcp.tool(name='memory_delete_record')(self.memory_delete_record)
        mcp.tool(name='memory_list_records')(self.memory_list_records)
        mcp.tool(name='memory_retrieve_records')(self.memory_retrieve_records)
        mcp.tool(name='memory_batch_create_records')(self.memory_batch_create_records)
        mcp.tool(name='memory_batch_update_records')(self.memory_batch_update_records)
        mcp.tool(name='memory_batch_delete_records')(self.memory_batch_delete_records)

    async def memory_get_record(
        self,
        ctx: Context,
        memory_id: Annotated[str, Field(description='Memory resource ID')],
        memory_record_id: Annotated[
            str,
            Field(description=('Memory record ID (40-50 chars). Pattern: mem-[a-zA-Z0-9-_]*')),
        ],
    ) -> MemoryRecordResponse | ErrorResponse:
        """Get a specific memory record from an AgentCore Memory resource.

        Returns the full record including content, metadata, namespaces,
        and strategy ID. This is a read-only operation.
        """
        logger.info(f'Getting memory record {memory_record_id} from {memory_id}')

        try:
            client = self._get_client()
            response = client.get_memory_record(
                memoryId=memory_id,
                memoryRecordId=memory_record_id,
            )

            return MemoryRecordResponse(
                status='success',
                message=f'Memory record {memory_record_id} retrieved.',
                memory_record=response.get('memoryRecord', {}),
            )
        except Exception as e:
            return handle_memory_error('GetMemoryRecord', e)

    async def memory_delete_record(
        self,
        ctx: Context,
        memory_id: Annotated[str, Field(description='Memory resource ID')],
        memory_record_id: Annotated[
            str,
            Field(description='Memory record ID to delete (pattern: mem-...)'),
        ],
    ) -> DeleteMemoryRecordResponse | ErrorResponse:
        """Permanently delete a memory record from an AgentCore Memory resource.

        WARNING: This permanently removes the memory record. This action
        cannot be undone.
        """
        logger.info(f'Deleting memory record {memory_record_id} from {memory_id}')

        try:
            client = self._get_client()
            response = client.delete_memory_record(
                memoryId=memory_id,
                memoryRecordId=memory_record_id,
            )

            return DeleteMemoryRecordResponse(
                status='success',
                message=f'Memory record {memory_record_id} deleted.',
                memory_record_id=response.get('memoryRecordId', memory_record_id),
            )
        except Exception as e:
            return handle_memory_error('DeleteMemoryRecord', e)

    async def memory_list_records(
        self,
        ctx: Context,
        memory_id: Annotated[str, Field(description='Memory resource ID')],
        namespace: Annotated[
            str,
            Field(
                description=(
                    'Namespace prefix filter (1-1024 chars). Returns all '
                    'records in namespaces starting with this prefix.'
                )
            ),
        ],
        memory_strategy_id: Annotated[
            str | None,
            Field(description='Filter by memory strategy ID'),
        ] = None,
        max_results: Annotated[
            int | None,
            Field(description='Max results per page (1-100, default 20)'),
        ] = None,
        next_token: Annotated[
            str | None,
            Field(description='Pagination token'),
        ] = None,
    ) -> ListMemoryRecordsResponse | ErrorResponse:
        """List memory records in an AgentCore Memory resource.

        Returns memory record summaries filtered by namespace and
        optionally by strategy. This is a read-only operation.
        """
        logger.info(f'Listing memory records in {memory_id}, namespace={namespace}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                'memoryId': memory_id,
                'namespace': namespace,
            }
            if memory_strategy_id is not None:
                kwargs['memoryStrategyId'] = memory_strategy_id
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token is not None:
                kwargs['nextToken'] = next_token

            response = client.list_memory_records(**kwargs)
            records = response.get('memoryRecordSummaries', [])

            return ListMemoryRecordsResponse(
                status='success',
                message=f'Found {len(records)} memory record(s).',
                memory_records=records,
                next_token=response.get('nextToken'),
            )
        except Exception as e:
            return handle_memory_error('ListMemoryRecords', e)

    async def memory_retrieve_records(
        self,
        ctx: Context,
        memory_id: Annotated[str, Field(description='Memory resource ID')],
        namespace: Annotated[
            str,
            Field(description='Namespace prefix filter (1-1024 chars)'),
        ],
        search_query: Annotated[
            str,
            Field(
                description=('Semantic search query for finding relevant records (1-10000 chars)')
            ),
        ],
        memory_strategy_id: Annotated[
            str | None,
            Field(description='Filter by memory strategy ID'),
        ] = None,
        top_k: Annotated[
            int | None,
            Field(description='Max top-scoring records to return (1-100)'),
        ] = None,
        max_results: Annotated[
            int | None,
            Field(description='Max results per page (1-100, default 20)'),
        ] = None,
        next_token: Annotated[
            str | None,
            Field(description='Pagination token'),
        ] = None,
    ) -> ListMemoryRecordsResponse | ErrorResponse:
        """Semantic search for memory records in an AgentCore Memory resource.

        COST WARNING: Semantic search invokes embedding and retrieval
        infrastructure. Each call incurs compute charges.

        Searches long-term memory records by semantic similarity to the
        query. Returns results ordered by relevance score. Use this to
        retrieve contextually relevant memories for agent responses.
        """
        logger.info(f'Retrieving memory records from {memory_id}, namespace={namespace}')

        try:
            client = self._get_client()
            search_criteria: dict[str, Any] = {
                'searchQuery': search_query,
            }
            if memory_strategy_id is not None:
                search_criteria['memoryStrategyId'] = memory_strategy_id
            if top_k is not None:
                search_criteria['topK'] = top_k

            kwargs: dict[str, Any] = {
                'memoryId': memory_id,
                'namespace': namespace,
                'searchCriteria': search_criteria,
            }
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token is not None:
                kwargs['nextToken'] = next_token

            response = client.retrieve_memory_records(**kwargs)
            records = response.get('memoryRecordSummaries', [])

            return ListMemoryRecordsResponse(
                status='success',
                message=f'Retrieved {len(records)} relevant memory record(s).',
                memory_records=records,
                next_token=response.get('nextToken'),
            )
        except Exception as e:
            return handle_memory_error('RetrieveMemoryRecords', e)

    async def memory_batch_create_records(
        self,
        ctx: Context,
        memory_id: Annotated[str, Field(description='Memory resource ID')],
        records: Annotated[
            list[dict[str, Any]],
            Field(
                description=(
                    'Records to create (0-100 items). Each record requires: '
                    '"content" (MemoryContent union, typically '
                    '{"text": "..."}), "namespaces" (list of 0-1 strings), '
                    '"requestIdentifier" (unique string 1-80 chars), '
                    '"timestamp" (epoch seconds). Optional: '
                    '"memoryStrategyId".'
                )
            ),
        ],
    ) -> BatchRecordsResponse | ErrorResponse:
        """Batch create memory records in an AgentCore Memory resource.

        COST WARNING: Creating memory records consumes storage and
        indexing resources. Each record incurs charges.

        Creates up to 100 memory records in a single call. Each record
        must include content, namespaces, a request identifier, and a
        timestamp.
        """
        logger.info(f'Batch creating {len(records)} records in {memory_id}')

        try:
            client = self._get_client()
            response = client.batch_create_memory_records(
                memoryId=memory_id,
                records=records,
            )

            successful = response.get('successfulRecords', [])
            failed = response.get('failedRecords', [])

            return BatchRecordsResponse(
                status='success' if not failed else 'partial',
                message=(f'{len(successful)} created, {len(failed)} failed.'),
                successful_records=successful,
                failed_records=failed,
            )
        except Exception as e:
            return handle_memory_error('BatchCreateMemoryRecords', e)

    async def memory_batch_update_records(
        self,
        ctx: Context,
        memory_id: Annotated[str, Field(description='Memory resource ID')],
        records: Annotated[
            list[dict[str, Any]],
            Field(
                description=(
                    'Records to update (0-100 items). Each requires: '
                    '"memoryRecordId" (pattern: mem-...), '
                    '"timestamp" (epoch seconds). Optional: '
                    '"content", "memoryStrategyId", "namespaces".'
                )
            ),
        ],
    ) -> BatchRecordsResponse | ErrorResponse:
        """Batch update memory records in an AgentCore Memory resource.

        Updates up to 100 memory records in a single call. Each record
        must include its ID and a timestamp.
        """
        logger.info(f'Batch updating {len(records)} records in {memory_id}')

        try:
            client = self._get_client()
            response = client.batch_update_memory_records(
                memoryId=memory_id,
                records=records,
            )

            successful = response.get('successfulRecords', [])
            failed = response.get('failedRecords', [])

            return BatchRecordsResponse(
                status='success' if not failed else 'partial',
                message=(f'{len(successful)} updated, {len(failed)} failed.'),
                successful_records=successful,
                failed_records=failed,
            )
        except Exception as e:
            return handle_memory_error('BatchUpdateMemoryRecords', e)

    async def memory_batch_delete_records(
        self,
        ctx: Context,
        memory_id: Annotated[str, Field(description='Memory resource ID')],
        records: Annotated[
            list[dict[str, Any]],
            Field(
                description=(
                    'Records to delete (0-100 items). Each requires: '
                    '"memoryRecordId" (pattern: mem-[a-zA-Z0-9-_]*).'
                )
            ),
        ],
    ) -> BatchRecordsResponse | ErrorResponse:
        """Batch delete memory records from an AgentCore Memory resource.

        WARNING: This permanently deletes up to 100 memory records in a
        single call. This action cannot be undone.
        """
        logger.info(f'Batch deleting {len(records)} records from {memory_id}')

        try:
            client = self._get_client()
            response = client.batch_delete_memory_records(
                memoryId=memory_id,
                records=records,
            )

            successful = response.get('successfulRecords', [])
            failed = response.get('failedRecords', [])

            return BatchRecordsResponse(
                status='success' if not failed else 'partial',
                message=(f'{len(successful)} deleted, {len(failed)} failed.'),
                successful_records=successful,
                failed_records=failed,
            )
        except Exception as e:
            return handle_memory_error('BatchDeleteMemoryRecords', e)
