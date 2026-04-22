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

"""Unit tests for Memory record tools."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory.models import (
    BatchRecordsResponse,
    DeleteMemoryRecordResponse,
    ErrorResponse,
    ListMemoryRecordsResponse,
    MemoryRecordResponse,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory.records import (
    RecordTools,
)
from botocore.exceptions import ClientError


class TestMemoryGetRecord:
    """Tests for memory_get_record."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns memory record details on success."""
        mock_boto3_client.get_memory_record.return_value = {
            'memoryRecord': {
                'memoryRecordId': 'mem-abc123',
                'content': {'text': 'User likes coffee'},
                'namespaces': ['users/u1/prefs'],
            }
        }
        tools = RecordTools(client_factory)
        result = await tools.memory_get_record(
            ctx=mock_ctx,
            memory_id='m',
            memory_record_id='mem-abc123',
        )
        assert isinstance(result, MemoryRecordResponse)
        assert result.status == 'success'
        assert result.memory_record['memoryRecordId'] == 'mem-abc123'

    @pytest.mark.asyncio
    async def test_not_found(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse when record not found."""
        mock_boto3_client.get_memory_record.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'GetMemoryRecord',
        )
        tools = RecordTools(client_factory)
        result = await tools.memory_get_record(
            ctx=mock_ctx,
            memory_id='m',
            memory_record_id='mem-bad',
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestMemoryDeleteRecord:
    """Tests for memory_delete_record."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Deletes record and returns record ID."""
        mock_boto3_client.delete_memory_record.return_value = {'memoryRecordId': 'mem-abc123'}
        tools = RecordTools(client_factory)
        result = await tools.memory_delete_record(
            ctx=mock_ctx,
            memory_id='m',
            memory_record_id='mem-abc123',
        )
        assert isinstance(result, DeleteMemoryRecordResponse)
        assert result.status == 'success'
        assert result.memory_record_id == 'mem-abc123'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.delete_memory_record.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'DeleteMemoryRecord',
        )
        tools = RecordTools(client_factory)
        result = await tools.memory_delete_record(
            ctx=mock_ctx,
            memory_id='m',
            memory_record_id='bad',
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestMemoryListRecords:
    """Tests for memory_list_records."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns list of memory records with pagination."""
        mock_boto3_client.list_memory_records.return_value = {
            'memoryRecordSummaries': [
                {'memoryRecordId': 'mem-1', 'content': {'text': 'f1'}},
                {'memoryRecordId': 'mem-2', 'content': {'text': 'f2'}},
            ],
            'nextToken': 'tok',
        }
        tools = RecordTools(client_factory)
        result = await tools.memory_list_records(
            ctx=mock_ctx,
            memory_id='m',
            namespace='users/u1/facts',
        )
        assert isinstance(result, ListMemoryRecordsResponse)
        assert result.status == 'success'
        assert len(result.memory_records) == 2
        assert result.next_token == 'tok'

    @pytest.mark.asyncio
    async def test_with_strategy_filter(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes strategy filter and pagination to API."""
        mock_boto3_client.list_memory_records.return_value = {'memoryRecordSummaries': []}
        tools = RecordTools(client_factory)
        await tools.memory_list_records(
            ctx=mock_ctx,
            memory_id='m',
            namespace='ns',
            memory_strategy_id='strat-1',
            max_results=10,
            next_token='tok',
        )
        kw = mock_boto3_client.list_memory_records.call_args.kwargs
        assert kw['memoryStrategyId'] == 'strat-1'
        assert kw['maxResults'] == 10
        assert kw['nextToken'] == 'tok'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.list_memory_records.side_effect = ClientError(
            {
                'Error': {'Code': 'ServiceException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 500},
            },
            'ListMemoryRecords',
        )
        tools = RecordTools(client_factory)
        result = await tools.memory_list_records(
            ctx=mock_ctx,
            memory_id='m',
            namespace='ns',
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestMemoryRetrieveRecords:
    """Tests for memory_retrieve_records (semantic search)."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns semantically relevant records with scores."""
        mock_boto3_client.retrieve_memory_records.return_value = {
            'memoryRecordSummaries': [
                {
                    'memoryRecordId': 'mem-1',
                    'score': 0.95,
                    'content': {'text': 'relevant memory'},
                },
            ],
        }
        tools = RecordTools(client_factory)
        result = await tools.memory_retrieve_records(
            ctx=mock_ctx,
            memory_id='m',
            namespace='users/u1',
            search_query='What does the user prefer?',
        )
        assert isinstance(result, ListMemoryRecordsResponse)
        assert result.status == 'success'
        assert len(result.memory_records) == 1
        assert result.memory_records[0]['score'] == 0.95

    @pytest.mark.asyncio
    async def test_with_all_params(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes topK, strategyId, and pagination params."""
        mock_boto3_client.retrieve_memory_records.return_value = {'memoryRecordSummaries': []}
        tools = RecordTools(client_factory)
        await tools.memory_retrieve_records(
            ctx=mock_ctx,
            memory_id='m',
            namespace='ns',
            search_query='query',
            top_k=5,
            memory_strategy_id='s1',
            max_results=10,
            next_token='tok',
        )
        kw = mock_boto3_client.retrieve_memory_records.call_args.kwargs
        assert kw['searchCriteria']['topK'] == 5
        assert kw['searchCriteria']['memoryStrategyId'] == 's1'
        assert kw['maxResults'] == 10
        assert kw['nextToken'] == 'tok'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.retrieve_memory_records.side_effect = ClientError(
            {
                'Error': {'Code': 'ServiceException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 500},
            },
            'RetrieveMemoryRecords',
        )
        tools = RecordTools(client_factory)
        result = await tools.memory_retrieve_records(
            ctx=mock_ctx,
            memory_id='m',
            namespace='ns',
            search_query='q',
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestMemoryBatchCreateRecords:
    """Tests for memory_batch_create_records."""

    @pytest.mark.asyncio
    async def test_all_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns success when all records created."""
        mock_boto3_client.batch_create_memory_records.return_value = {
            'successfulRecords': [
                {'memoryRecordId': 'mem-1', 'status': 'CREATED'},
            ],
            'failedRecords': [],
        }
        tools = RecordTools(client_factory)
        result = await tools.memory_batch_create_records(
            ctx=mock_ctx,
            memory_id='m',
            records=[
                {
                    'content': {'text': 'hello'},
                    'namespaces': ['ns'],
                    'requestIdentifier': 'req-1',
                    'timestamp': 1700000000,
                }
            ],
        )
        assert isinstance(result, BatchRecordsResponse)
        assert result.status == 'success'
        assert len(result.successful_records) == 1
        assert len(result.failed_records) == 0

    @pytest.mark.asyncio
    async def test_partial_failure(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns partial status when some records fail."""
        mock_boto3_client.batch_create_memory_records.return_value = {
            'successfulRecords': [{'memoryRecordId': 'mem-1'}],
            'failedRecords': [{'requestIdentifier': 'req-2', 'errorMessage': 'bad'}],
        }
        tools = RecordTools(client_factory)
        result = await tools.memory_batch_create_records(
            ctx=mock_ctx,
            memory_id='m',
            records=[],
        )
        assert isinstance(result, BatchRecordsResponse)
        assert result.status == 'partial'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.batch_create_memory_records.side_effect = ClientError(
            {
                'Error': {'Code': 'ServiceException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 500},
            },
            'BatchCreateMemoryRecords',
        )
        tools = RecordTools(client_factory)
        result = await tools.memory_batch_create_records(
            ctx=mock_ctx,
            memory_id='m',
            records=[],
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestMemoryBatchUpdateRecords:
    """Tests for memory_batch_update_records."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns success when all records updated."""
        mock_boto3_client.batch_update_memory_records.return_value = {
            'successfulRecords': [{'memoryRecordId': 'mem-1'}],
            'failedRecords': [],
        }
        tools = RecordTools(client_factory)
        result = await tools.memory_batch_update_records(
            ctx=mock_ctx,
            memory_id='m',
            records=[
                {
                    'memoryRecordId': 'mem-1',
                    'timestamp': 1700000000,
                }
            ],
        )
        assert isinstance(result, BatchRecordsResponse)
        assert result.status == 'success'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.batch_update_memory_records.side_effect = ClientError(
            {
                'Error': {'Code': 'ServiceException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 500},
            },
            'BatchUpdateMemoryRecords',
        )
        tools = RecordTools(client_factory)
        result = await tools.memory_batch_update_records(
            ctx=mock_ctx,
            memory_id='m',
            records=[],
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestMemoryBatchDeleteRecords:
    """Tests for memory_batch_delete_records."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns success when all records deleted."""
        mock_boto3_client.batch_delete_memory_records.return_value = {
            'successfulRecords': [{'memoryRecordId': 'mem-1'}],
            'failedRecords': [],
        }
        tools = RecordTools(client_factory)
        result = await tools.memory_batch_delete_records(
            ctx=mock_ctx,
            memory_id='m',
            records=[{'memoryRecordId': 'mem-1'}],
        )
        assert isinstance(result, BatchRecordsResponse)
        assert result.status == 'success'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on service error."""
        mock_boto3_client.batch_delete_memory_records.side_effect = ClientError(
            {
                'Error': {'Code': 'ServiceException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 500},
            },
            'BatchDeleteMemoryRecords',
        )
        tools = RecordTools(client_factory)
        result = await tools.memory_batch_delete_records(
            ctx=mock_ctx,
            memory_id='m',
            records=[],
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
